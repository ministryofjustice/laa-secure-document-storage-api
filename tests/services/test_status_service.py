from src.models.status_report import StatusReport, Category, ServiceObservations


def test_serviceobservations_add_check():
    so = ServiceObservations()

    a = so.add_check('a')

    assert len(so.observations) == 1
    assert a.category == Category.failure


def test_serviceobservations_add_checks():
    so = ServiceObservations()

    a, b, c = so.add_checks('a', 'b', 'c')

    assert len(so.observations) == 3
    assert a.category == b.category == c.category == Category.failure
    assert so.has_failures()


def test_serviceobservations_check_outcome_mixed():
    so = ServiceObservations()
    a, b, c = so.add_checks('a', 'b', 'c')

    # Only a single outcome set to success
    a.category = Category.success

    assert len(so.observations) == 3
    assert so.has_failures()


def test_serviceobservations_check_outcome_success():
    so = ServiceObservations()
    a, b, c = so.add_checks('a', 'b', 'c')

    # All outcomes are success
    a.category = b.category = c.category = Category.success

    assert len(so.observations) == 3
    assert so.has_failures() is False


def test_report_single_service_success():
    so = ServiceObservations()
    a, b = so.add_checks('a', 'b')
    a.category = b.category = Category.success

    report = StatusReport(services=[so, ])

    assert report.has_failures() is False


def test_report_multiple_service_success():
    so = ServiceObservations()
    a, b = so.add_checks('a', 'b')
    a.category = b.category = Category.success
    so_other = ServiceObservations()
    ao, bo = so_other.add_checks('a', 'b')
    ao.category = bo.category = Category.success

    report = StatusReport(services=[so, so_other])

    assert report.has_failures() is False


def test_report_single_service_mixed():
    so = ServiceObservations()
    a, b = so.add_checks('a', 'b')
    a.category = Category.success
    # b outcome is left at failure

    report = StatusReport(services=[so, ])

    assert report.has_failures()


def test_report_multiple_service_mixed():
    so = ServiceObservations()
    a, b = so.add_checks('a', 'b')
    a.category = b.category = Category.success
    so_other = ServiceObservations()
    ao, bo = so_other.add_checks('a', 'b')
    ao.category = Category.success
    # bo is left at failure

    report = StatusReport(services=[so, so_other])

    assert report.has_failures()
