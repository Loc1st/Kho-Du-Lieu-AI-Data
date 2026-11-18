from mvc.models.sql_model import run_custom_query
from mvc.views.view import render_json
class SqlController:
    @staticmethod
    def handle_execute_sql(payload): return render_json(run_custom_query(payload.get('database','phone_dw'),payload.get('sql','')))
