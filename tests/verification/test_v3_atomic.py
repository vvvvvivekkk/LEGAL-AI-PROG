"""V3 tests: atomic decomposition + fidelity scoring."""

from src.generation.parser import Claim
from src.verification.types import Entailment
from src.verification.v3_atomic import check_fidelity, decompose


def test_decompose_splits_on_and():
    atoms = decompose("The deposit is two months rent and must be refunded in thirty days")
    assert len(atoms) == 2
    assert "two months rent" in atoms[0]
    assert "thirty days" in atoms[1]


def test_decompose_splits_on_semicolon():
    atoms = decompose("First part; second part; third part")
    assert len(atoms) == 3


def test_decompose_single_claim_returns_one_atom():
    atoms = decompose("A single indivisible statement")
    assert atoms == ["A single indivisible statement"]


def test_full_fidelity_when_all_atoms_entail(context_chunks, make_nli):
    nli = make_nli(
        [
            ("two months", "two months", Entailment.ENTAILS, 0.9),
            ("thirty days", "thirty days", Entailment.ENTAILS, 0.95),
        ]
    )
    claim = Claim(
        "The deposit is two months rent and must be refunded in thirty days",
        ["urban_tenancy_act_2019::s4:a", "urban_tenancy_act_2019::s4:b"],
    )
    result = check_fidelity(claim, context_chunks, nli)
    assert result.fidelity == 1.0
    assert all(a.entailed for a in result.atoms)


def test_partial_fidelity_when_one_atom_unsupported(context_chunks, make_nli):
    # Only the "thirty days" atom is entailed; the fabricated "waived entirely"
    # atom finds no support -> fidelity 0.5.
    nli = make_nli([("thirty days", "thirty days", Entailment.ENTAILS, 0.95)])
    claim = Claim(
        "The deposit must be refunded in thirty days and the fee is waived entirely",
        ["urban_tenancy_act_2019::s4:b"],
    )
    result = check_fidelity(claim, context_chunks, nli)
    assert result.fidelity == 0.5
    assert len(result.atoms) == 2


def test_fidelity_dict_is_serializable(context_chunks, make_nli):
    nli = make_nli([])
    claim = Claim("A single statement", ["urban_tenancy_act_2019::s4:a"])
    d = check_fidelity(claim, context_chunks, nli).to_dict()
    assert set(d.keys()) == {"claim_text", "fidelity", "atoms"}
