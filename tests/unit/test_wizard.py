"""Tests for the self-service Setup Wizard, templates, and tutorials."""

from __future__ import annotations

import pytest

from xcapitsff.selfservice.wizard import (
    FormField,
    SetupWizard,
    WizardProgress,
    WizardStep,
)
from xcapitsff.selfservice.templates_catalog import (
    IndustryTemplate,
    TemplateCatalog,
)
from xcapitsff.selfservice.tutorials import (
    Tutorial,
    TutorialManager,
    TutorialStep,
)


# ===================================================================
# Wizard — step progression
# ===================================================================


class TestWizardStepProgression:
    def test_start_wizard_returns_progress(self):
        wizard = SetupWizard()
        progress = wizard.start_wizard("tenant-1")
        assert isinstance(progress, WizardProgress)
        assert progress.tenant_id == "tenant-1"
        assert progress.current_step == "company_profile"
        assert progress.started_at != ""

    def test_start_wizard_first_step_is_company_profile(self):
        wizard = SetupWizard()
        wizard.start_wizard("tenant-2")
        step = wizard.get_current_step("tenant-2")
        assert step.step_id == "company_profile"
        assert step.title == "Perfil de tu empresa"

    def test_submit_step_advances_to_next(self):
        wizard = SetupWizard()
        wizard.start_wizard("t1")
        progress = wizard.submit_step("t1", "company_profile", {
            "company_name": "Acme",
            "industry": "fintech",
            "company_size": "1-10",
            "primary_market": "LATAM",
        })
        assert progress.current_step == "team_setup"
        assert "company_profile" in progress.completed_steps

    def test_full_progression_through_all_steps(self):
        wizard = SetupWizard()
        wizard.start_wizard("t-full")

        # Step 1 — company_profile
        wizard.submit_step("t-full", "company_profile", {
            "company_name": "TestCo",
            "industry": "tech",
            "company_size": "11-50",
            "primary_market": "Global",
        })

        # Step 2 — team_setup
        wizard.submit_step("t-full", "team_setup", {
            "default_role": "user",
        })

        # Step 3 — sales_config
        wizard.submit_step("t-full", "sales_config", {
            "use_sales": True,
        })

        # Step 4 — support_config
        wizard.submit_step("t-full", "support_config", {
            "use_support": True,
        })

        # Step 5 — import_data (skip)
        wizard.skip_step("t-full", "import_data")

        # Step 6 — agent_config
        wizard.submit_step("t-full", "agent_config", {
            "enable_agents": True,
        })

        # Step 7 — integrations (skip)
        wizard.skip_step("t-full", "integrations")

        progress = wizard.get_progress("t-full")
        assert progress.current_step == "review_and_launch"
        assert len(progress.completed_steps) == 5
        assert len(progress.skipped_steps) == 2


# ===================================================================
# Wizard — skip step
# ===================================================================


class TestWizardSkipStep:
    def test_skip_skippable_step(self):
        wizard = SetupWizard()
        wizard.start_wizard("t-skip")

        # Advance to import_data (step 5)
        wizard.submit_step("t-skip", "company_profile", {
            "company_name": "X", "industry": "tech",
            "company_size": "1-10", "primary_market": "LATAM",
        })
        wizard.submit_step("t-skip", "team_setup", {"default_role": "user"})
        wizard.submit_step("t-skip", "sales_config", {"use_sales": True})
        wizard.submit_step("t-skip", "support_config", {"use_support": True})

        progress = wizard.skip_step("t-skip", "import_data")
        assert "import_data" in progress.skipped_steps
        assert progress.current_step == "agent_config"

    def test_skip_non_skippable_step_raises(self):
        wizard = SetupWizard()
        wizard.start_wizard("t-no-skip")
        with pytest.raises(ValueError, match="no se puede omitir"):
            wizard.skip_step("t-no-skip", "company_profile")

    def test_skip_wrong_step_raises(self):
        wizard = SetupWizard()
        wizard.start_wizard("t-wrong-skip")
        with pytest.raises(ValueError, match="El paso actual"):
            wizard.skip_step("t-wrong-skip", "import_data")


# ===================================================================
# Wizard — go back
# ===================================================================


class TestWizardGoBack:
    def test_go_back_one_step(self):
        wizard = SetupWizard()
        wizard.start_wizard("t-back")
        wizard.submit_step("t-back", "company_profile", {
            "company_name": "B", "industry": "tech",
            "company_size": "1-10", "primary_market": "LATAM",
        })
        assert wizard.get_progress("t-back").current_step == "team_setup"

        progress = wizard.go_back("t-back")
        assert progress.current_step == "company_profile"

    def test_go_back_from_first_step_raises(self):
        wizard = SetupWizard()
        wizard.start_wizard("t-back-first")
        with pytest.raises(ValueError, match="primer paso"):
            wizard.go_back("t-back-first")


# ===================================================================
# Wizard — submit with validation
# ===================================================================


class TestWizardValidation:
    def test_missing_required_field_raises(self):
        wizard = SetupWizard()
        wizard.start_wizard("t-val")
        with pytest.raises(ValueError, match="obligatorio"):
            wizard.submit_step("t-val", "company_profile", {
                "company_name": "X",
                # missing industry, company_size, primary_market
            })

    def test_invalid_select_value_raises(self):
        wizard = SetupWizard()
        wizard.start_wizard("t-val2")
        with pytest.raises(ValueError, match="inv\u00e1lido"):
            wizard.submit_step("t-val2", "company_profile", {
                "company_name": "X",
                "industry": "invalid_industry",
                "company_size": "1-10",
                "primary_market": "LATAM",
            })

    def test_submit_wrong_step_raises(self):
        wizard = SetupWizard()
        wizard.start_wizard("t-val3")
        with pytest.raises(ValueError, match="El paso actual"):
            wizard.submit_step("t-val3", "team_setup", {"default_role": "user"})

    def test_submit_without_active_wizard_raises(self):
        wizard = SetupWizard()
        with pytest.raises(ValueError, match="No hay wizard activo"):
            wizard.submit_step("ghost-tenant", "company_profile", {})


# ===================================================================
# Wizard — complete wizard applies config
# ===================================================================


class TestWizardComplete:
    def _advance_to_review(self, wizard: SetupWizard, tenant_id: str):
        wizard.start_wizard(tenant_id)
        wizard.submit_step(tenant_id, "company_profile", {
            "company_name": "LaunchCo", "industry": "fintech",
            "company_size": "51-200", "primary_market": "LATAM",
        })
        wizard.submit_step(tenant_id, "team_setup", {"default_role": "admin"})
        wizard.submit_step(tenant_id, "sales_config", {
            "use_sales": True, "scoring_model": "advanced",
        })
        wizard.submit_step(tenant_id, "support_config", {
            "use_support": True, "sla_enabled": True,
        })
        wizard.skip_step(tenant_id, "import_data")
        wizard.submit_step(tenant_id, "agent_config", {
            "enable_agents": True, "agent_tone": "friendly",
        })
        wizard.skip_step(tenant_id, "integrations")

    def test_complete_wizard_returns_summary(self):
        wizard = SetupWizard()
        self._advance_to_review(wizard, "t-launch")
        result = wizard.complete_wizard("t-launch")
        assert result["status"] == "completed"
        assert result["tenant_id"] == "t-launch"
        assert result["steps_completed"] == 5
        assert result["steps_skipped"] == 2

    def test_complete_wizard_applies_configuration(self):
        wizard = SetupWizard()
        self._advance_to_review(wizard, "t-apply")
        result = wizard.complete_wizard("t-apply")
        applied = result["configuration_applied"]
        assert "sales" in applied["features_enabled"]
        assert "support" in applied["features_enabled"]
        assert "agents" in applied["features_enabled"]
        assert applied["settings_applied"]["sales"]["scoring_model"] == "advanced"
        assert applied["settings_applied"]["agents"]["tone"] == "friendly"

    def test_complete_wizard_before_finishing_steps_raises(self):
        wizard = SetupWizard()
        wizard.start_wizard("t-incomplete")
        with pytest.raises(ValueError, match="debe completarse"):
            wizard.complete_wizard("t-incomplete")


# ===================================================================
# Industry templates
# ===================================================================


class TestTemplateCatalog:
    def test_list_templates_returns_all(self):
        catalog = TemplateCatalog()
        templates = catalog.list_templates()
        assert len(templates) == 5
        ids = {t.template_id for t in templates}
        assert ids == {"fintech", "saas", "consulting", "ecommerce", "startup"}

    def test_get_template_returns_correct_one(self):
        catalog = TemplateCatalog()
        t = catalog.get_template("fintech")
        assert t is not None
        assert t.name == "Fintech / Crypto"
        assert t.recommended_plan == "professional"

    def test_get_template_unknown_returns_none(self):
        catalog = TemplateCatalog()
        assert catalog.get_template("nonexistent") is None


# ===================================================================
# Template application
# ===================================================================


class TestTemplateApplication:
    def test_apply_template_returns_config(self):
        catalog = TemplateCatalog()
        result = catalog.apply_template("tenant-tpl", "saas")
        assert result["tenant_id"] == "tenant-tpl"
        assert result["template_applied"] == "saas"
        assert "sales" in result["features_enabled"]
        assert len(result["pipeline_stages"]) == 6

    def test_apply_unknown_template_raises(self):
        catalog = TemplateCatalog()
        with pytest.raises(ValueError, match="no encontrado"):
            catalog.apply_template("t", "does_not_exist")

    def test_fintech_template_has_8_stages(self):
        catalog = TemplateCatalog()
        t = catalog.get_template("fintech")
        assert t is not None
        assert len(t.pipeline_stages) == 8

    def test_ecommerce_template_has_4_stages(self):
        catalog = TemplateCatalog()
        t = catalog.get_template("ecommerce")
        assert t is not None
        assert len(t.pipeline_stages) == 4


# ===================================================================
# Tutorial lifecycle
# ===================================================================


class TestTutorialLifecycle:
    def test_list_tutorials_returns_all(self):
        manager = TutorialManager()
        tutorials = manager.list_tutorials()
        assert len(tutorials) == 6

    def test_list_tutorials_filter_by_audience(self):
        manager = TutorialManager()
        admin_tutorials = manager.list_tutorials(audience="admin")
        assert all(t.target_audience == "admin" for t in admin_tutorials)
        assert len(admin_tutorials) >= 1

    def test_start_tutorial_returns_steps(self):
        manager = TutorialManager()
        tutorial = manager.start_tutorial("t-tut", "first_lead")
        assert tutorial.tutorial_id == "first_lead"
        assert len(tutorial.steps) == 3
        assert all(not s.completed for s in tutorial.steps)

    def test_complete_step_marks_completed(self):
        manager = TutorialManager()
        manager.start_tutorial("t-tut2", "first_lead")
        tutorial = manager.complete_step("t-tut2", "first_lead", 1)
        step1 = [s for s in tutorial.steps if s.step_number == 1][0]
        assert step1.completed is True

    def test_complete_all_steps_marks_tutorial_done(self):
        manager = TutorialManager()
        manager.start_tutorial("t-tut3", "first_ticket")
        manager.complete_step("t-tut3", "first_ticket", 1)
        manager.complete_step("t-tut3", "first_ticket", 2)
        manager.complete_step("t-tut3", "first_ticket", 3)
        progress = manager.get_progress("t-tut3")
        assert progress["tutorials"]["first_ticket"]["status"] == "completed"

    def test_start_nonexistent_tutorial_raises(self):
        manager = TutorialManager()
        with pytest.raises(ValueError, match="no encontrado"):
            manager.start_tutorial("t", "nope")

    def test_complete_step_without_starting_raises(self):
        manager = TutorialManager()
        with pytest.raises(ValueError, match="no fue iniciado"):
            manager.complete_step("t-ghost", "first_lead", 1)


# ===================================================================
# Progress tracking
# ===================================================================


class TestProgressTracking:
    def test_wizard_progress_tracks_configuration(self):
        wizard = SetupWizard()
        wizard.start_wizard("t-cfg")
        wizard.submit_step("t-cfg", "company_profile", {
            "company_name": "ProgCo", "industry": "consulting",
            "company_size": "11-50", "primary_market": "Iberia",
        })
        progress = wizard.get_progress("t-cfg")
        assert "company_profile" in progress.configuration
        assert progress.configuration["company_profile"]["company_name"] == "ProgCo"

    def test_tutorial_progress_empty_for_new_tenant(self):
        manager = TutorialManager()
        progress = manager.get_progress("brand-new")
        assert progress["tenant_id"] == "brand-new"
        assert progress["tutorials"] == {}

    def test_tutorial_progress_shows_in_progress(self):
        manager = TutorialManager()
        manager.start_tutorial("t-prog", "use_dashboard")
        manager.complete_step("t-prog", "use_dashboard", 1)
        progress = manager.get_progress("t-prog")
        tut = progress["tutorials"]["use_dashboard"]
        assert tut["status"] == "in_progress"
        assert tut["steps_completed"] == 1
        assert tut["total_steps"] == 3
