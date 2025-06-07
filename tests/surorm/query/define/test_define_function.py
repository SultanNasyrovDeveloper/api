from surorm.query import DefineFunction


def test_define_function_simple():
    name = 'fn::test_name'
    body = 'return 5'
    query = DefineFunction(name).body(body).sql()
    assert query == f'define function {name} () {{ {body}; }}'


def test_define_function_overwrite():
    name = 'fn::test_name'
    body = 'return 5'
    query = DefineFunction(name).body(body).overwrite(True).sql()
    assert query == f'define function overwrite {name} () {{ {body}; }}'


def test_define_if_not_exists():
    name = 'fn::test_name'
    body = 'return 5'
    query = DefineFunction(name).body(body).if_not_exists(True).sql()
    assert query == f'define function if not exists {name} () {{ {body}; }}'


def test_define_with_comment():
    name = 'fn::test_name'
    body = 'return 5'
    comment = 'test_comment'
    query = DefineFunction(name).body(body).comment(comment).sql()
    assert query == f'define function {name} () {{ {body}; }} comment {comment}'
