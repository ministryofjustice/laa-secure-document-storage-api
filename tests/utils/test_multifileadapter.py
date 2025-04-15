import casbin
import pytest

from src.utils.multifileadapter import MultiFileAdapter


@pytest.fixture(scope="module")
def casbin_acl_model():
    model = casbin.Model()
    model.load_model_from_text("""
    [request_definition]
    r = sub, obj, act
    [policy_definition]
    p = sub, obj, act
    [policy_effect]
    e = some(where (p.eft == allow))
    [matchers]
    m = r.sub == p.sub && r.obj == p.obj && regexMatch(r.act, p.act)
    """)
    return model


def test_multifile_adapter_single_specified_file(tmp_path, casbin_acl_model):
    policy_path = tmp_path / "policy.csv"
    with open(policy_path, "w") as f:
        f.write("p,test_user,/fake_route,GET\n")
    enforcer = casbin.Enforcer(
        model=casbin_acl_model,
        adapter=MultiFileAdapter(policy_path),
    )
    assert enforcer.enforce('test_user', '/fake_route', 'GET')


def test_multifile_adapter_multiple_specified_files(tmp_path, casbin_acl_model):
    policy_path_a = tmp_path / "policy_a.csv"
    policy_path_b = tmp_path / "policy_b.csv"
    with open(policy_path_a, "w") as f:
        f.write("p,test_user,/fake_route_a,GET\n")
    with open(policy_path_b, "w") as f:
        f.write("p,test_user,/fake_route_b,GET\n")

    combined_paths = f"{policy_path_a}:{policy_path_b}"

    enforcer = casbin.Enforcer(
        model=casbin_acl_model,
        adapter=MultiFileAdapter(combined_paths),
    )
    assert enforcer.enforce('test_user', '/fake_route_a', 'GET') \
           and enforcer.enforce('test_user', '/fake_route_b', 'GET')


def test_multifile_adapter_mixed_dir_and_file(tmp_path, casbin_acl_model):
    subdir_path = tmp_path / "subdir"
    subdir_path.mkdir()
    policy_path_a = tmp_path / "policy_a.csv"
    policy_path_b = subdir_path / "policy_b.csv"
    with open(policy_path_a, "w") as f:
        f.write("p,test_user,/fake_route_a,GET\n")
    with open(policy_path_b, "w") as f:
        f.write("p,test_user,/fake_route_b,GET\n")

    combined_paths = f"{policy_path_a}:{subdir_path}"

    enforcer = casbin.Enforcer(
        model=casbin_acl_model,
        adapter=MultiFileAdapter(combined_paths),
    )
    assert enforcer.enforce('test_user', '/fake_route_a', 'GET') \
           and enforcer.enforce('test_user', '/fake_route_b', 'GET')


def test_multifile_adapter_directory(tmp_path, casbin_acl_model):
    with open(tmp_path / "policy_a.csv", "w") as f:
        f.write("p,test_user,/fake_route_a,GET\n")
    with open(tmp_path / "policy_b.csv", "w") as f:
        f.write("p,test_user,/fake_route_b,GET\n")
    enforcer = casbin.Enforcer(
        model=casbin_acl_model,
        adapter=MultiFileAdapter(tmp_path),
    )
    assert enforcer.enforce('test_user', '/fake_route_a', 'GET') \
           and enforcer.enforce('test_user', '/fake_route_b', 'GET')


def test_multifile_adapter_ignores_noncsv(tmp_path, casbin_acl_model):
    with open(tmp_path / "policy_a.txt", "w") as f:
        f.write("p,test_user,/fake_route_a,GET\n")
    with open(tmp_path / "policy_b.csv", "w") as f:
        f.write("p,test_user,/fake_route_b,GET\n")
    enforcer = casbin.Enforcer(
        model=casbin_acl_model,
        adapter=MultiFileAdapter(tmp_path),
    )
    assert not enforcer.enforce('test_user', '/fake_route_a', 'GET') \
           and enforcer.enforce('test_user', '/fake_route_b', 'GET')


def test_multifile_adapter_case_insensitive(tmp_path, casbin_acl_model):
    with open(tmp_path / "policy_a.CSV", "w") as f:
        f.write("p,test_user,/fake_route_a,GET\n")
    with open(tmp_path / "policy_b.cSv", "w") as f:
        f.write("p,test_user,/fake_route_b,GET\n")
    enforcer = casbin.Enforcer(
        model=casbin_acl_model,
        adapter=MultiFileAdapter(tmp_path),
    )
    assert enforcer.enforce('test_user', '/fake_route_a', 'GET') \
           and enforcer.enforce('test_user', '/fake_route_b', 'GET')


def test_multifile_adapter_strips_quotes(tmp_path, casbin_acl_model):
    policy_path_a = tmp_path / "policy_a.csv"
    policy_path_b = tmp_path / "policy_b.csv"
    with open(policy_path_a, "w") as f:
        f.write("p,test_user,/fake_route_a,GET\n")
    with open(policy_path_b, "w") as f:
        f.write("p,test_user,/fake_route_b,GET\n")

    # Note the extra quote marks surrounding the joined pair
    combined_paths = f"'{policy_path_a}:{policy_path_b}'"

    enforcer = casbin.Enforcer(
        model=casbin_acl_model,
        adapter=MultiFileAdapter(combined_paths),
    )
    assert enforcer.enforce('test_user', '/fake_route_a', 'GET') \
           and enforcer.enforce('test_user', '/fake_route_b', 'GET')
