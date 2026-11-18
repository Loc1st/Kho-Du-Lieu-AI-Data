from mvc.models.etl_model import execute_test_suite,get_etl_and_quality_data
from mvc.views.view import render_json
class EtlController:
    @staticmethod
    def handle_get_data(): return render_json(get_etl_and_quality_data())
    @staticmethod
    def handle_run_tests(): return render_json({'tests':execute_test_suite()})
