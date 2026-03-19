"""Tests for conversational onboarding."""

from xcapitsff.selfservice.conversational_onboarding import (
    OnboardingState,
    extract_onboarding_data,
    generate_onboarding_response,
    get_next_question,
)


def test_extract_company_name():
    state = OnboardingState(tenant_id="t1")
    state, extracted = extract_onboarding_data('La empresa se llama "Fintech Austral SA"', state)
    assert state.company_name == "Fintech Austral SA"


def test_extract_company_quoted():
    state = OnboardingState(tenant_id="t1")
    state, _ = extract_onboarding_data('La empresa se llama "CryptoVault"', state)
    assert state.company_name is not None


def test_extract_industry_fintech():
    state = OnboardingState(tenant_id="t1")
    state, _ = extract_onboarding_data("Somos una fintech que hace pagos", state)
    assert state.industry == "fintech"


def test_extract_industry_tech():
    state = OnboardingState(tenant_id="t1")
    state, _ = extract_onboarding_data("Hacemos software como servicio", state)
    assert state.industry == "technology"


def test_extract_size_number():
    state = OnboardingState(tenant_id="t1")
    state, _ = extract_onboarding_data("Somos 25 personas", state)
    assert state.company_size == "11-50"


def test_extract_size_startup():
    state = OnboardingState(tenant_id="t1")
    state, _ = extract_onboarding_data("Somos una startup", state)
    assert state.company_size == "1-10"


def test_extract_market_latam():
    state = OnboardingState(tenant_id="t1")
    state, _ = extract_onboarding_data("Operamos en Argentina y México", state)
    assert state.market == "LATAM"


def test_extract_market_iberia():
    state = OnboardingState(tenant_id="t1")
    state, _ = extract_onboarding_data("Estamos en España", state)
    assert state.market == "Iberia"


def test_extract_import_csv():
    state = OnboardingState(tenant_id="t1")
    state, _ = extract_onboarding_data("Tenemos los datos en un Excel", state)
    assert state.import_source == "csv"


def test_extract_import_salesforce():
    state = OnboardingState(tenant_id="t1")
    state, _ = extract_onboarding_data("Usamos Salesforce", state)
    assert state.import_source == "salesforce"


def test_full_conversation():
    state = OnboardingState(tenant_id="t1")
    state, _ = extract_onboarding_data('Somos "Acme Corp", una fintech de Buenos Aires con 30 personas', state)
    assert state.company_name == "Acme Corp"
    assert state.industry == "fintech"
    assert state.market == "LATAM"
    assert state.company_size == "11-50"


def test_next_question_starts_with_name():
    state = OnboardingState(tenant_id="t1")
    q = get_next_question(state)
    assert "empresa" in q.lower()


def test_next_question_industry_after_name():
    state = OnboardingState(tenant_id="t1", company_name="Acme")
    q = get_next_question(state)
    assert "industria" in q.lower()


def test_ready_when_complete():
    state = OnboardingState(tenant_id="t1", company_name="Acme", industry="fintech")
    assert state.is_ready is True


def test_generate_response_asks_next():
    state = OnboardingState(tenant_id="t1")
    resp, state, visual = generate_onboarding_response("Hola", state)
    assert "empresa" in resp.lower()
    assert visual is not None


def test_generate_response_complete():
    state = OnboardingState(
        tenant_id="t1", company_name="Acme", industry="fintech",
        company_size="11-50", market="LATAM",
    )
    state.completed_topics = ["import"]
    resp, state, visual = generate_onboarding_response("Listo", state)
    assert "configuración" in resp.lower() or "workspace" in resp.lower()


def test_completion_rate():
    state = OnboardingState(tenant_id="t1", company_name="Acme")
    assert state.completion_rate > 0
    assert state.completion_rate < 100


def test_language_iberia():
    state = OnboardingState(tenant_id="t1")
    state, _ = extract_onboarding_data("Estamos en Madrid, España", state)
    assert state.agent_language == "es_iberia"
