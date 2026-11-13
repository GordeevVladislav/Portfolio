import os
import unittest

try:
    import yaml
except ImportError:  # PyYAML необязателен
    yaml = None

PATH = os.path.join(os.path.dirname(__file__), "..", "docs", "05-api", "openapi.yaml")


@unittest.skipIf(yaml is None, "PyYAML не установлен")
class OpenApiTests(unittest.TestCase):
    def setUp(self):
        with open(PATH, encoding="utf-8") as f:
            self.spec = yaml.safe_load(f)

    def test_endpoint_and_method(self):
        self.assertIn("post", self.spec["paths"]["/api/v1/cart/add"])

    def test_documented_error_statuses(self):
        responses = self.spec["paths"]["/api/v1/cart/add"]["post"]["responses"]
        self.assertEqual(set(responses), {"200", "401", "404", "409", "422"})

    def test_all_refs_resolve(self):
        def walk(node):
            if isinstance(node, dict):
                for k, v in node.items():
                    if k == "$ref":
                        name = v.split("/")[-1]
                        self.assertIn(name, self.spec["components"]["schemas"], v)
                    else:
                        walk(v)
            elif isinstance(node, list):
                for v in node:
                    walk(v)
        walk(self.spec)

    def test_quantity_bounds_match_implementation(self):
        q = self.spec["components"]["schemas"]["AddToCartRequest"]["properties"]["quantity"]
        self.assertEqual((q["minimum"], q["maximum"]), (1, 10))


if __name__ == "__main__":
    unittest.main()
