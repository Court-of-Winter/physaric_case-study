import json

from enron_analysis.privacy import _node_signatures, assess_reidentification


def test_structural_degree_counts_unique_neighbors_across_months():
    signatures = _node_signatures(
        {
            ("2001-01", "source", "target"): 2,
            ("2001-02", "source", "target"): 3,
        },
        "structural",
    )

    assert signatures["source"] == (1, 0, 5, 0)
    assert signatures["target"] == (0, 1, 0, 5)


def test_privacy_assessment_documents_simulated_and_mailbox_access_scenarios():
    raw = {
        ("2001-01", "alice.private@example.com", "bob.private@example.com"): 5,
        ("2001-01", "bob.private@example.com", "alice.private@example.com"): 2,
        ("2001-02", "alice.private@example.com", "carol.private@example.com"): 3,
        ("2001-02", "carol.private@example.com", "alice.private@example.com"): 1,
    }
    pseudonymized = {
        ("2001-01", "person_a", "person_b"): 5,
        ("2001-01", "person_b", "person_a"): 2,
        ("2001-02", "person_a", "person_c"): 3,
        ("2001-02", "person_c", "person_a"): 1,
    }

    report = assess_reidentification(
        {"person": raw},
        {"person": pseudonymized},
        min_edge_count=2,
    )
    serialized = json.dumps(report)
    scenarios = report["scenarios"]
    simulated_scenario = scenarios["simulated_public_information"]
    mailbox_scenario = scenarios["public_mailbox_corpus_access"]
    person = mailbox_scenario["networks"]["person"]

    assert simulated_scenario["status"] == "not_evaluated"
    assert "does not have the mailboxes" in simulated_scenario["attacker_assumption"]
    assert simulated_scenario["preparation_status"] == "inputs_available"
    assert (
        simulated_scenario["identity_reference"]["name_address_header_records"]
        > 0
    )
    assert (
        simulated_scenario["public_organizational_chart"]["entity_count"] == 11
    )
    assert (
        simulated_scenario["public_organizational_chart"]["relationship_count"]
        == 10
    )
    assert (
        simulated_scenario["methods"]["name_and_address_linkage"]["status"]
        == "not_evaluable"
    )
    assert (
        simulated_scenario["methods"]["department_to_graph_matching"][
            "status"
        ]
        == "not_evaluable"
    )
    assert mailbox_scenario["status"] == "evaluated"
    assert person["attack_results"]["structural"]["before_mitigation"][
        "unique_match_rate"
    ] == 1
    assert person["attack_results"]["temporal"]["after_mitigation"][
        "unique_match_rate"
    ] == 1
    assert (
        person["utility"]["retention_fraction"]["interactions"]
        == 10 / 11
    )
    assert person["utility"]["retention_fraction"]["nodes"] == 1
    assert set(person["threshold_sensitivity"]) >= {
        "5",
        "10",
        "25",
        "50",
        "100",
    }
    assert "attack_results" in person["threshold_sensitivity"]["10"]
    for private_value in (
        "alice.private@example.com",
        "bob.private@example.com",
        "carol.private@example.com",
        "person_a",
    ):
        assert private_value not in serialized


def test_privacy_assessment_rejects_nonpositive_suppression_threshold():
    try:
        assess_reidentification({}, {}, min_edge_count=0)
    except ValueError as error:
        assert "at least 1" in str(error)
    else:
        raise AssertionError("zero suppression threshold should be rejected")
