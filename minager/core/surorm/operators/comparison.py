from .base import MultiOperandOperator, TwoOperandOperator


class Or(MultiOperandOperator):
    operation = 'OR'


class And(MultiOperandOperator):
    operation = 'AND'


class Greater(TwoOperandOperator):
    operation = '>'


class GTE(TwoOperandOperator):
    operation = '>='


class Less(TwoOperandOperator):
    operation = '<'


class LTE(TwoOperandOperator):
    operation = '<='


class Equals(TwoOperandOperator):
    operation = '=='
