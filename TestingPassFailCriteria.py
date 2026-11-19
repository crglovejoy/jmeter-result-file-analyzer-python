import unittest

from PassFailCriteria import PassFailCriteria
from PassFailCriteria import PassFailCriteriaCollection


class TestPassFailCriteria(unittest.TestCase):
    def setUp(self):
        PassFailCriteria.set_valid_metric_list(["testmetric"])

    def tearDown(self):
        PassFailCriteria.set_valid_metric_list([])

    def test_analysis_supports_all_operators(self):
        test_cases = [
            (23.0, ">", True),
            (21.0, "<", True),
            (22.0, "=", True),
            (22.0, ">", False),
            (22.0, "<", False),
            (23.0, "=", False),
        ]

        for value, operator, expected in test_cases:
            with self.subTest(value=value, operator=operator):
                criteria = PassFailCriteria("testlabel", "testmetric", operator, 22.0)
                self.assertEqual(
                    criteria.execute_pass_fail_analysis_and_return_passed_bool(
                        value, criteria
                    ),
                    expected,
                )

    def test_constructor_strips_label_and_operator(self):
        criteria = PassFailCriteria(" testlabel ", "testmetric", " > ", 22.0)

        self.assertEqual(criteria.label, "testlabel")
        self.assertEqual(criteria.operator, ">")
        self.assertEqual(criteria.metric, "testmetric")
        self.assertEqual(criteria.threshold_value, 22.0)

    def test_constructor_rejects_unsupported_metric(self):
        with self.assertRaisesRegex(NotImplementedError, "unsupportedmetric"):
            PassFailCriteria("testlabel", "unsupportedmetric", ">", 22.0)

    def test_constructor_rejects_unsupported_operator(self):
        with self.assertRaisesRegex(ValueError, "!="):
            PassFailCriteria("testlabel", "testmetric", "!=", 22.0)


class TestPassFailCriteriaCollection(unittest.TestCase):
    def setUp(self):
        PassFailCriteria.set_valid_metric_list(
            ["metric1", "metric2", "metric3"]
        )

    def tearDown(self):
        PassFailCriteria.set_valid_metric_list([])

    def test_collection_starts_empty(self):
        criteria_collection = PassFailCriteriaCollection()

        self.assertEqual(len(criteria_collection.pf_criteria_dict), 0)

    def test_create_and_populate_collection_from_string(self):
        criteria_collection = PassFailCriteriaCollection.create_and_populate_pf_criteria_collection(
            "label1:metric1:>:22.0|label2:metric2:<:23.0|label3:metric3:=:25.0"
        )

        self.assertEqual(len(criteria_collection.pf_criteria_dict), 3)
        expected = {
            "label1_metric1": ("label1", "metric1", ">", 22.0),
            "label2_metric2": ("label2", "metric2", "<", 23.0),
            "label3_metric3": ("label3", "metric3", "=", 25.0),
        }
        for key, values in expected.items():
            with self.subTest(key=key):
                criteria = criteria_collection.pf_criteria_dict[key]
                self.assertEqual(
                    (
                        criteria.label,
                        criteria.metric,
                        criteria.operator,
                        criteria.threshold_value,
                    ),
                    values,
                )

    def test_create_empty_collection_from_empty_or_whitespace_string(self):
        for criteria_string in ("", "   "):
            with self.subTest(criteria_string=criteria_string):
                criteria_collection = (
                    PassFailCriteriaCollection.create_and_populate_pf_criteria_collection(
                        criteria_string
                    )
                )
                self.assertEqual(len(criteria_collection.pf_criteria_dict), 0)

    def test_create_collection_rejects_malformed_criteria(self):
        with self.assertRaisesRegex(ValueError, "Expected 4 items"):
            PassFailCriteriaCollection.create_and_populate_pf_criteria_collection(
                "label1:metric1:>:22.0|malformed"
            )

    def test_create_collection_rejects_duplicate_criteria(self):
        with self.assertRaisesRegex(ValueError, "already exists"):
            PassFailCriteriaCollection.create_and_populate_pf_criteria_collection(
                "label1:metric1:>:22.0|label1:metric1:<:23.0"
            )

    def test_criteria_mapping_is_read_only(self):
        criteria_collection = PassFailCriteriaCollection.create_and_populate_pf_criteria_collection(
            "label1:metric1:>:22.0"
        )

        with self.assertRaises(TypeError):
            criteria_collection.pf_criteria_dict["label2_metric2"] = (
                PassFailCriteria("label2", "metric2", ">", 20.0)
            )

    def test_find_and_execute_returns_success_and_failure_details(self):
        criteria_collection = PassFailCriteriaCollection.create_and_populate_pf_criteria_collection(
            "label1:metric1:>:22.0"
        )

        self.assertEqual(
            criteria_collection.find_and_execute_pass_fail_criteria_and_return_success(
                "label1", "metric1", 23.0
            ),
            (
                True,
                True,
                "",
                "label=label1 : metric=metric1 : 23.00 > 22.00 was TRUE\n",
            ),
        )
        self.assertEqual(
            criteria_collection.find_and_execute_pass_fail_criteria_and_return_success(
                "label1", "metric1", 21.0
            ),
            (
                True,
                False,
                "label=label1 : metric=metric1 : 21.00 > 22.00 was FALSE\n",
                "",
            ),
        )

    def test_find_and_execute_returns_not_found_for_unknown_criteria(self):
        criteria_collection = PassFailCriteriaCollection()

        self.assertEqual(
            criteria_collection.find_and_execute_pass_fail_criteria_and_return_success(
                "unknown", "metric1", 23.0
            ),
            (False, False, "", ""),
        )


if __name__ == "__main__":
    unittest.main()
