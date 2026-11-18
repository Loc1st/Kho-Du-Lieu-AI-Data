from mvc.models.scd2_model import get_store_scd2_detail,search_stores,simulate_scd2_change
from mvc.views.view import render_json
class Scd2Controller:
    @staticmethod
    def handle_get_detail(params): return render_json(get_store_scd2_detail(params.get('ma_cua_hang','CH00')))
    @staticmethod
    def handle_search(params): return render_json(search_stores(params.get('q','')))
    @staticmethod
    def handle_change_region(payload): return render_json(simulate_scd2_change(payload))
