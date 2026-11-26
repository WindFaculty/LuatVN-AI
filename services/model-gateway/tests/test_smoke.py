import json
import pathlib
import unittest

from luatvn_ai_model_gateway import CONTRACTS_VERSION, SERVICE_NAME


class SkeletonSmokeTest(unittest.TestCase):
    def test_metadata_matches_module(self) -> None:
        meta = json.loads(pathlib.Path("repo-meta.json").read_text(encoding="utf-8"))
        self.assertEqual(meta["name"], SERVICE_NAME)
        self.assertEqual(meta["contracts_version"], CONTRACTS_VERSION)
        self.assertEqual(meta["visibility"], "PRIVATE")


if __name__ == "__main__":
    unittest.main()
