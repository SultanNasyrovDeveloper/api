from .base import MultiOperandOperator


class Add(MultiOperandOperator):
    operation = '+'


class Multiple(MultiOperandOperator):
    operation = '*'
