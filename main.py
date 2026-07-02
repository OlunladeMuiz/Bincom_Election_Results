from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from db import fetch_all, execute_write

app = FastAPI()
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent / "templates"))


@app.get("/", response_class=HTMLResponse)
def polling_unit_page(request: Request, unit_id: Optional[str] = None):
    try:
        polling_units = fetch_all(
            """
            SELECT
                uniqueid,
                COALESCE(
                    NULLIF(
                        CONCAT_WS(
                            ' - ',
                            NULLIF(BTRIM(polling_unit_name), ''),
                            NULLIF(BTRIM(polling_unit_number), '')
                        ),
                        ''
                    ),
                    uniqueid::text
                ) AS polling_unit_label
            FROM polling_unit
            ORDER BY NULLIF(BTRIM(polling_unit_name), '') NULLS LAST,
                     NULLIF(BTRIM(polling_unit_number), '') NULLS LAST,
                     uniqueid
            """
        )
    except RuntimeError as err:
        return templates.TemplateResponse(request, "polling_unit.html", {
            "request": request,
            "error": str(err),
            "polling_units": [],
            "results": None,
            "selected_unit": None,
        })

    results = None
    selected_unit = None
    error = None

    unit_key = unit_id.strip() if unit_id else None

    if unit_id is not None and not unit_key:
        error = "Please select a polling unit before submitting."
    elif unit_key:
        try:
            results = fetch_all(
                """
                SELECT party_abbreviation, party_score
                FROM announced_pu_results
                WHERE polling_unit_uniqueid = %s
                ORDER BY party_abbreviation
                """,
                (unit_key,)
            )
            match = [u for u in polling_units if str(u.get("uniqueid")) == unit_key]
            selected_unit = (match[0].get("polling_unit_label") or unit_key) if match else unit_key
            if not results and not error:
                error = "No results found for this polling unit."
        except RuntimeError as err:
            error = str(err)

    return templates.TemplateResponse(request, "polling_unit.html", {
        "request": request,
        "polling_units": polling_units,
        "results": results,
        "selected_unit": selected_unit,
        "error": error,
    })


@app.get("/lga-results", response_class=HTMLResponse)
def lga_results_page(request: Request, lga_id: Optional[str] = None):
    try:
        lgas = fetch_all(
            "SELECT lga_id, lga_name FROM lga ORDER BY lga_name"
        )
    except RuntimeError as err:
        return templates.TemplateResponse(request, "lga_results.html", {
            "request": request,
            "error": str(err),
            "lgas": [],
            "results": None,
            "selected_lga": None,
        })

    results = None
    selected_lga = None
    error = None

    lga_key = lga_id.strip() if lga_id else None

    if lga_id is not None and not lga_key:
        error = "Please select an LGA before submitting."
    elif lga_key:
        try:
            lga_id_value = int(lga_key)
        except ValueError:
            error = "Please select a valid LGA."
        else:
            try:
                # Must NOT use announced_lga_results table.
                # announced_pu_results.polling_unit_uniqueid is VARCHAR holding polling_unit.uniqueid.
                # polling_unit.lga_id matches lga.lga_id.
                results = fetch_all(
                    """
                    SELECT apr.party_abbreviation, SUM(apr.party_score) AS total_score
                    FROM announced_pu_results apr
                    JOIN polling_unit pu
                      ON pu.uniqueid = CAST(apr.polling_unit_uniqueid AS INTEGER)
                    WHERE pu.lga_id = %s
                    GROUP BY apr.party_abbreviation
                    ORDER BY apr.party_abbreviation
                    """,
                    (lga_id_value,)
                )
                match = [lg for lg in lgas if lg.get("lga_id") == lga_id_value]
                selected_lga = (match[0].get("lga_name") or f"LGA {lga_id_value}") if match else f"LGA {lga_id_value}"
                if not results and not error:
                    error = "No polling unit results found for this LGA."
            except RuntimeError as err:
                error = str(err)

    return templates.TemplateResponse(request, "lga_results.html", {
        "request": request,
        "lgas": lgas,
        "results": results,
        "selected_lga": selected_lga,
        "error": error,
    })


@app.get("/add-result", response_class=HTMLResponse)
def add_result_form(request: Request):
    try:
        polling_units = fetch_all(
            """
            SELECT
                uniqueid,
                COALESCE(
                    NULLIF(
                        CONCAT_WS(
                            ' - ',
                            NULLIF(BTRIM(polling_unit_name), ''),
                            NULLIF(BTRIM(polling_unit_number), '')
                        ),
                        ''
                    ),
                    uniqueid::text
                ) AS polling_unit_label
            FROM polling_unit
            ORDER BY NULLIF(BTRIM(polling_unit_name), '') NULLS LAST,
                     NULLIF(BTRIM(polling_unit_number), '') NULLS LAST,
                     uniqueid
            """
        )
        parties = fetch_all(
            "SELECT DISTINCT party_abbreviation FROM announced_pu_results ORDER BY party_abbreviation"
        )
    except RuntimeError as err:
        return templates.TemplateResponse(request, "add_result.html", {
            "request": request,
            "error": str(err),
            "polling_units": [],
            "parties": [],
            "success": False,
            "selected_unit": None,
        })

    return templates.TemplateResponse(request, "add_result.html", {
        "request": request,
        "polling_units": polling_units,
        "parties": parties,
        "success": False,
        "error": None,
        "selected_unit": None,
    })


@app.post("/add-result", response_class=HTMLResponse)
async def add_result_submit(request: Request):
    try:
        polling_units = fetch_all(
            """
            SELECT
                uniqueid,
                COALESCE(
                    NULLIF(
                        CONCAT_WS(
                            ' - ',
                            NULLIF(BTRIM(polling_unit_name), ''),
                            NULLIF(BTRIM(polling_unit_number), '')
                        ),
                        ''
                    ),
                    uniqueid::text
                ) AS polling_unit_label
            FROM polling_unit
            ORDER BY NULLIF(BTRIM(polling_unit_name), '') NULLS LAST,
                     NULLIF(BTRIM(polling_unit_number), '') NULLS LAST,
                     uniqueid
            """
        )
        parties = fetch_all(
            "SELECT DISTINCT party_abbreviation FROM announced_pu_results ORDER BY party_abbreviation"
        )
    except RuntimeError as err:
        return templates.TemplateResponse(request, "add_result.html", {
            "request": request,
            "error": str(err),
            "polling_units": [],
            "parties": [],
            "success": False,
            "selected_unit": None,
        })

    form = await request.form()
    unit_id = form.get("polling_unit_uniqueid", "").strip()

    if not unit_id:
        return templates.TemplateResponse(request, "add_result.html", {
            "request": request,
            "polling_units": polling_units,
            "parties": parties,
            "error": "Please select a polling unit before submitting.",
            "success": False,
            "selected_unit": unit_id,
        })

    client_ip = request.client.host if request.client else "127.0.0.1"
    errors = []
    inserted = 0

    for party in parties:
        abbr = party["party_abbreviation"]
        score_raw = form.get(f"score_{abbr}", "").strip()
        if not score_raw:
            continue
        if not score_raw.isdigit():
            errors.append(f"{abbr}: score must be a whole number, got '{score_raw}'.")
            continue
        try:
            execute_write(
                """
                INSERT INTO announced_pu_results
                    (polling_unit_uniqueid, party_abbreviation, party_score,
                     entered_by_user, date_entered, user_ip_address)
                VALUES (%s, %s, %s, %s, NOW(), %s)
                """,
                (unit_id, abbr, int(score_raw), "bincom_app", client_ip)
            )
            inserted += 1
        except RuntimeError as err:
            errors.append(f"{abbr}: {err}")

    if inserted == 0 and not errors:
        return templates.TemplateResponse(request, "add_result.html", {
            "request": request,
            "polling_units": polling_units,
            "parties": parties,
            "error": "No scores were entered. Please fill in at least one party score.",
            "success": False,
            "selected_unit": unit_id,
        })

    if errors:
        return templates.TemplateResponse(request, "add_result.html", {
            "request": request,
            "polling_units": polling_units,
            "parties": parties,
            "error": " | ".join(errors),
            "success": inserted > 0,
            "selected_unit": unit_id,
        })

    return templates.TemplateResponse(request, "add_result.html", {
        "request": request,
        "polling_units": polling_units,
        "parties": parties,
        "success": True,
        "error": None,
        "selected_unit": unit_id,
    })
