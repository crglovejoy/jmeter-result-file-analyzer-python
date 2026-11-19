from types import MappingProxyType
from typing import Final, Mapping

def greater_than_result(value: float, threshold_value: float) -> bool:
    return value > threshold_value

def lesser_than_result(value: float, threshold_value: float) -> bool:
    return value < threshold_value

def equal_to_result(value: float, threshold_value: float) -> bool:
    return value == threshold_value




class PassFailCriteria:
    __slots__ = ("__label", "__operator", "__metric", "__threshold_value", "__func")

    __valid_metric_list: list[str] = []

    @classmethod
    def set_valid_metric_list(cls, valid_metric_list: list[str]):
        cls.__valid_metric_list = valid_metric_list

    def __init__(self, label: str, metric: str, operator: str, threshold_value: float):
        if (metric not in self.__valid_metric_list):
            raise NotImplementedError(f"{metric} is not a supported metric type")
        
        self.__label = label.strip()
        self.__operator = operator.strip()
        self.__metric = metric.strip()
        self.__threshold_value = threshold_value
        if (self.__operator == ">"):
            self.__func = staticmethod(greater_than_result)
        elif (self.__operator == "<"):
            self.__func = staticmethod(lesser_than_result)
        elif (self.__operator == "="):
            self.__func = staticmethod(equal_to_result)
        else:
            raise ValueError(f"{self.__operator} is an unsupported operator")

    @property
    def label(self) -> str:
        return self.__label

    @property
    def operator(self) -> str:
        return self.__operator
    
    @property
    def threshold_value(self) -> float:
        return self.__threshold_value

    @property
    def metric(self) -> str:
        return self.__metric

    @staticmethod
    def execute_pass_fail_analysis_and_return_passed_bool(value, passFailCriteria: PassFailCriteria) -> bool:
        return passFailCriteria.__func(value, passFailCriteria.threshold_value)


class PassFailCriteriaCollection:
    __slots__ = ("__pf_criteria_dict")

    def __init__(self):
        self.__pf_criteria_dict: dict[str, PassFailCriteria] = {}

    @property
    def pf_criteria_dict(self) -> Mapping[str, PassFailCriteria]:
        return MappingProxyType(self.__pf_criteria_dict)

    @classmethod
    def __get_dict_key_from_pass_fail_criteria(cls, pass_fail_criteria: PassFailCriteria):
        return cls.__get_dict_key(pass_fail_criteria.label, pass_fail_criteria.metric)

    @classmethod
    def __get_dict_key(cls, label: str, metric: str) -> str:
        return f"{label}_{metric}"
    
    @staticmethod
    def create_and_populate_pf_criteria_collection(pf_criteria_str: str) -> PassFailCriteriaCollection:
        pass_fail_coll = PassFailCriteriaCollection()

        if not pf_criteria_str:
            return pass_fail_coll
        if not pf_criteria_str.strip():
            return pass_fail_coll
        
        criteria_items = pf_criteria_str.split("|")
        for item in criteria_items:
            criteria = item.split(":")
            if len(criteria) != 4:
                raise ValueError(f"Expected 4 items in a criteria and got {len(criteria)}: {criteria}")

            pass_fail_coll.add_pass_fail_criteria(PassFailCriteria(criteria[0].strip(), criteria[1].strip(), 
                criteria[2].strip(), float(criteria[3].strip()))
            )

        return pass_fail_coll


    def add_pass_fail_criteria(self, pass_fail_criteria: PassFailCriteria):
        key_str = self.__get_dict_key_from_pass_fail_criteria(pass_fail_criteria)
        if self.__pf_criteria_dict.get(key_str):
            raise ValueError(f"a pass fail criteria already exists for {pass_fail_criteria.label} : {pass_fail_criteria.metric}")
        self.__pf_criteria_dict[key_str] = pass_fail_criteria


    def find_and_execute_pass_fail_criteria_and_return_success(self, label: str, metric: str, value: float) -> tuple[bool, bool, str, str]:
        found: bool = False
        passed: bool = False
        fail_str: str = ""
        pass_str: str = ""
        pass_fail_criteria = self.__pf_criteria_dict.get(self.__get_dict_key(label, metric))

        if pass_fail_criteria:
            found = True
            passed = pass_fail_criteria.execute_pass_fail_analysis_and_return_passed_bool(value, pass_fail_criteria)
            if not passed:
                fail_str = f"label={label} : metric={metric} : {value:.2f} {pass_fail_criteria.operator} {pass_fail_criteria.threshold_value:.2f} was FALSE\n"
            else:
                pass_str = f"label={label} : metric={metric} : {value:.2f} {pass_fail_criteria.operator} {pass_fail_criteria.threshold_value:.2f} was TRUE\n"

        return found, passed, fail_str, pass_str
        
        

    
