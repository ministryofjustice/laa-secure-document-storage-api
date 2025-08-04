from src.models.status_report import StatusReport, Outcome, ServiceObservations


def test_serviceobservations_add_check():
    so = ServiceObservations()

    a = so.add_check('a')

    assert len(so.checks) == 1
    assert a.outcome == Outcome.failure


def test_serviceobservations_add_checks():
    so = ServiceObservations()

    a, b, c = so.add_checks('a', 'b', 'c')

    assert len(so.checks) == 3
    assert a.outcome == b.outcome == c.outcome == Outcome.failure
    assert so.has_failures()


def test_serviceobservations_check_outcome_mixed():
    so = ServiceObservations()
    a, b, c = so.add_checks('a', 'b', 'c')

    # Only a single outcome set to success
    a.outcome = Outcome.success

    assert len(so.checks) == 3
    assert so.has_failures()


def test_serviceobservations_check_outcome_success():
    so = ServiceObservations()
    a, b, c = so.add_checks('a', 'b', 'c')

    # All outcomes are success
    a.outcome = b.outcome = c.outcome = Outcome.success

    assert len(so.checks) == 3
    assert so.has_failures() is False


def test_report_single_service_success():
    so = ServiceObservations()
    a, b = so.add_checks('a', 'b')
    a.outcome = b.outcome = Outcome.success

    report = StatusReport(services=[so, ])

    assert report.has_failures() is False


def test_report_multiple_service_success():
    so = ServiceObservations()
    a, b = so.add_checks('a', 'b')
    a.outcome = b.outcome = Outcome.success
    so_other = ServiceObservations()
    ao, bo = so_other.add_checks('a', 'b')
    ao.outcome = bo.outcome = Outcome.success

    report = StatusReport(services=[so, so_other])

    assert report.has_failures() is False


def test_report_single_service_mixed():
    so = ServiceObservations()
    a, b = so.add_checks('a', 'b')
    a.outcome = Outcome.success
    # b outcome is left at failure

    report = StatusReport(services=[so, ])

    assert report.has_failures()


def test_report_multiple_service_mixed():
    so = ServiceObservations()
    a, b = so.add_checks('a', 'b')
    a.outcome = b.outcome = Outcome.success
    so_other = ServiceObservations()
    ao, bo = so_other.add_checks('a', 'b')
    ao.outcome = Outcome.success
    # bo is left at failure

    report = StatusReport(services=[so, so_other])

    assert report.has_failures()
