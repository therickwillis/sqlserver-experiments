import os
from flask import Flask, render_template_string, redirect
import pyodbc
from dotenv import load_dotenv

load_dotenv()

# Configuration - prefer a full connection string, otherwise build from parts
DB_CONN_STRING = os.getenv('DB_CONN_STRING')
DB_DRIVER = os.getenv('DB_DRIVER', 'ODBC Driver 18 for SQL Server')
DB_SERVER = os.getenv('DB_SERVER', 'localhost,1433')
DB_DATABASE = os.getenv('DB_DATABASE', 'EnchantedBeesDB')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')

# Auto-select an available ODBC driver if the configured one isn't installed
def _select_available_driver(preferred):
  try:
    available = pyodbc.drivers()
  except Exception:
    available = []
  if preferred in available:
    return preferred, available
  for choice in ("ODBC Driver 18 for SQL Server", "ODBC Driver 17 for SQL Server", "FreeTDS"):
    if choice in available:
      return choice, available
  for d in available:
    if d.startswith("ODBC Driver") or d.startswith("FreeTDS"):
      return d, available
  if "SQL Server" in available:
    return "SQL Server", available
  return preferred, available


if not DB_CONN_STRING:
  # ensure the driver name exists on this machine; auto-pick a suitable one
  DB_DRIVER, _available_drivers = _select_available_driver(DB_DRIVER)

if DB_CONN_STRING:
    CONNECTION_STRING = DB_CONN_STRING
else:
    if DB_USER and DB_PASSWORD:
        CONNECTION_STRING = (
            f"DRIVER={{{DB_DRIVER}}};"
            f"SERVER={DB_SERVER};"
            f"DATABASE={DB_DATABASE};"
            f"UID={DB_USER};PWD={DB_PASSWORD}"
        )
    else:
        # Trusted connection (Windows) fallback
        CONNECTION_STRING = (
            f"DRIVER={{{DB_DRIVER}}};"
            f"SERVER={DB_SERVER};"
            f"DATABASE={DB_DATABASE};"
            "Trusted_Connection=yes;"
        )

# Print basic connection info (avoid exposing passwords)
print("Using ODBC driver:", DB_DRIVER, "server:", DB_SERVER, "database:", DB_DATABASE)

def _print_driver_diagnostics(err):
  try:
    available = pyodbc.drivers()
  except Exception:
    available = []
  print("\nConnection error:", err)
  print("Available ODBC drivers:", available)
  print("If the driver above isn't listed, install the Microsoft ODBC Driver for SQL Server (17/18), or set DB_DRIVER/DB_CONN_STRING.")

app = Flask(__name__)

HTML_TEMPLATE = """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Species - Bee Admin</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
  </head>
  <body class="p-4">
    <div class="container">
      <h1 class="mb-4">Species</h1>
      <table class="table table-striped">
        <thead>
          <tr><th>Id</th><th>Name</th><th>Description</th></tr>
        </thead>
        <tbody>
          {% for s in species %}
          <tr>
            <td>{{ s.Id }}</td>
            <td>{{ s.Name }}</td>
            <td>{{ s.Description }}</td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
  </body>
</html>
"""


def get_species():
    query = "SELECT Id, Name, Description FROM dbo.Species ORDER BY Id"
    rows = []
    conn = None
    try:
      conn = pyodbc.connect(CONNECTION_STRING, autocommit=True)
      cur = conn.cursor()
      cur.execute(query)
      cols = [c[0] for c in cur.description]
      for r in cur.fetchall():
        rows.append(dict(zip(cols, r)))
    except pyodbc.InterfaceError as ie:
      _print_driver_diagnostics(ie)
      raise
    finally:
      if conn:
        conn.close()
    return rows


@app.route('/')
def index():
    return redirect('/species')


@app.route('/species')
def species_view():
    species = get_species()
    return render_template_string(HTML_TEMPLATE, species=species)


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
