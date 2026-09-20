import json
import uuid
from datetime import datetime

from flask import Flask, jsonify, request

app = Flask(__name__)

charges = {}
customers = {}
chaos_mode = None


@app.route("/v3/customers", methods=["POST"])
def create_customer():
    data = request.get_json()
    customer_id = f"cus_{uuid.uuid4().hex[:16]}"
    customers[customer_id] = {**data, "id": customer_id}
    return jsonify({"id": customer_id, **data}), 200


@app.route("/v3/payments", methods=["POST"])
def create_charge():
    if chaos_mode == "erro_500":
        return jsonify({"error": "Internal error"}), 500
    if chaos_mode == "timeout_apos_criar":
        data = request.get_json()
        charge_id = f"pay_{uuid.uuid4().hex[:16]}"
        charges[charge_id] = {
            "id": charge_id,
            "status": "PENDING",
            "value": data.get("value", 0),
            "reference": data.get("externalReference", ""),
            "billingType": data.get("billingType", "PIX"),
            "invoiceUrl": f"https://sandbox.asaas.com/i/{charge_id}",
            "dateCreated": datetime.utcnow().isoformat(),
        }
        return "", 504
    if chaos_mode == "429":
        return jsonify({"error": "Rate limit exceeded"}), 429

    data = request.get_json()
    charge_id = f"pay_{uuid.uuid4().hex[:16]}"
    charges[charge_id] = {
        "id": charge_id,
        "status": "PENDING",
        "value": data.get("value", 0),
        "reference": data.get("externalReference", ""),
        "billingType": data.get("billingType", "PIX"),
        "invoiceUrl": f"https://sandbox.asaas.com/i/{charge_id}",
        "dateCreated": datetime.utcnow().isoformat(),
        "split": data.get("split", []),
    }
    return jsonify(charges[charge_id]), 200


@app.route("/v3/payments/<charge_id>", methods=["GET"])
def get_charge(charge_id):
    if charge_id in charges:
        return jsonify(charges[charge_id]), 200
    return jsonify({"error": "not found"}), 404


@app.route("/v3/payments", methods=["GET"])
def search_charges():
    ref = request.args.get("externalReference")
    if ref:
        for c in charges.values():
            if c.get("reference") == ref:
                return jsonify({"data": [c], "totalCount": 1}), 200
    return jsonify({"data": list(charges.values()), "totalCount": len(charges)}), 200


@app.route("/v3/payments/<charge_id>/refund", methods=["POST"])
def refund_charge(charge_id):
    if charge_id not in charges:
        return jsonify({"error": "not found"}), 404
    charges[charge_id]["status"] = "REFUNDED"
    return jsonify(charges[charge_id]), 200


@app.route("/_sim/pay", methods=["POST"])
def sim_pay():
    data = request.get_json()
    pagamento_id = data.get("pagamento_id")
    for charge_id, charge in charges.items():
        if charge.get("reference") == pagamento_id:
            charge["status"] = "RECEIVED"
            return jsonify(charge), 200
    return jsonify({"error": "not found"}), 404


@app.route("/_sim/chaos", methods=["POST"])
def sim_chaos():
    global chaos_mode
    data = request.get_json()
    chaos_mode = data.get("cenario")
    return jsonify({"chaos_mode": chaos_mode}), 200


@app.route("/_sim/webhook", methods=["POST"])
def sim_webhook():
    data = request.get_json()
    target_url = data.get("url")
    event = data.get("event")
    import urllib.request

    req = urllib.request.Request(
        target_url,
        data=json.dumps(event).encode(),
        headers={
            "Content-Type": "application/json",
            "asaas-access-token": "token123",
        },
        method="POST",
    )
    try:
        urllib.request.urlopen(req, timeout=5)
        return jsonify({"sent": True}), 200
    except Exception as e:
        return jsonify({"sent": False, "error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
