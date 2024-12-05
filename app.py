from flask import Flask, request, render_template_string
from abacusai import ApiClient
import dateutil.parser
import logging
import webbrowser
from threading import Timer

api_key = 's2_771c05ba79d349f3ae6b62bbef3217ca'
client = ApiClient(api_key) 

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

PROJECT_ID = "1531b15134"

def get_latest_deployment_info():
    try:
        deployments = client.list_deployments(project_id=PROJECT_ID)
        sorted_deployments = sorted(deployments, key=lambda d: dateutil.parser.parse(d.created_at), reverse=True)
        
        if not sorted_deployments:
            raise ValueError("No deployments found for the project.")
        
        latest_deployment = sorted_deployments[0]
        deployment_tokens = client.list_deployment_tokens(project_id=PROJECT_ID)
        
        if not deployment_tokens:
            raise ValueError("No deployment tokens found for the project.")
        
        logging.info(f"Using deployment ID: {latest_deployment.id}")
        return latest_deployment.id, deployment_tokens[0].deployment_token
    except Exception as e:
        logging.error(f"Error fetching deployment info: {str(e)}")
        raise

def get_supplier_info(supplier_id, country):
    try:
        sql_query = f"""
        SELECT 
        parent_name,
        supplier_category,
        avg_shipping_cost
        FROM gold_suppliers
        WHERE supplier_id = '{supplier_id}' AND country = '{country}'
        """
        result = client.execute_feature_group_sql(sql_query)
        if not result.empty:
            return result.iloc[0].to_dict()
        return None
    except Exception as e:
        logging.error(f"Error fetching supplier info: {str(e)}")
        return None

def predict_shipping_cost(data):
    try:
        deployment_id, deployment_token = get_latest_deployment_info()
        
        supplier_info = get_supplier_info(data['supplier_id'], data['country'])
        if supplier_info is not None:
            data.update(supplier_info)
        else:
            logging.warning(f"No information found for supplier {data['supplier_id']} in {data['country']}. Using default values.")
            data['parent_name'] = " "
            data['supplier_category'] = " "
            data['avg_shipping_cost'] = " "

        query_data = {
            "organization_id": data.get('organization_id'),
            "customer_name": data.get('customer_name'),
            "supplier_id": data.get('supplier_id'),
            "supplier_name": data.get('supplier_name'),
            "supplier_parent_name": data['parent_name'],
            "supplier_country_avg_shipping_cost":data['avg_shipping_cost'],
            "vendorpo_supplier_category": data['supplier_category'],
            "country": data.get('country'),
            "transaction_type": "reseller",
            "order_created_date": data.get('order_created_date'),
            "order_purchase_type": "quote",
            "ship_to_address_line_1": data.get('ship_to_address_line_1'),
            "ship_to_city": data.get('ship_to_city'),
            "ship_to_region": data.get('ship_to_region'),
            "ship_to_country": data.get('ship_to_country'),
            "quotation_number": data.get('quotation_number')
        }
        
        result = client.predict(
            deployment_token=deployment_token,
            deployment_id=deployment_id,
            query_data=query_data
        )
        predicted_cost = result.get('ship_cost_in_lc', 'Prediction not available')
        if isinstance(predicted_cost, (int, float)):
            predicted_cost = round(predicted_cost, 2)
            ship_fee = round(1.25 * predicted_cost, 2)
            return predicted_cost, ship_fee
 
        else:
            return predicted_cost, 'Cannot calculate'
    except Exception as e:
        logging.error(f"Error in prediction: {str(e)}")
        return 'Error in prediction', 'Cannot calculate'

@app.route('/', methods=['GET', 'POST'])
def index():
    html_template = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Quote Shipping Costs Predictor</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            line-height: 1.4;
            margin: 20px;
            display: flex;
            flex-direction: column;
            align-items: center;
        }
        .container {
            display: flex;
            flex-wrap: wrap;
            max-width: 900px;
            width: 100%;
            gap: 20px;
        }
        .form-container, .result-container {
            flex: 1;
            min-width: 300px;
            padding: 20px;
            border: 1px solid #ccc;
            border-radius: 8px;
            box-shadow: 2px 2px 8px rgba(0, 0, 0, 0.1);
        }
        .form-container h2, .result-container h2 {
            text-align: center;
            margin-bottom: 20px;
        }
        label {
            display: block;
            margin-top: 10px;
        }
        input[type="text"], input[type="date"] {
            width: 100%;
            padding: 8px;
            margin-top: 5px;
        }
        input[type="submit"] {
            display: block;
            width: 100%;
            padding: 10px;
            margin-top: 20px;
            background-color: #4CAF50;
            color: white;
            border: none;
            cursor: pointer;
            border-radius: 4px;
        }
        input[type="submit"]:hover {
            background-color: #45a049;
        }
        .result-container p {
            font-size: 1.2em;
            margin: 10px 0;
        }
        .hidden {
            display: none;
        }
    </style>
</head>
<body>
    <h1>Quote Shipping Costs Predictor</h1>
    <div class="container">
        <!-- Form Section -->
        <div class="form-container">
            <h2>Enter Details</h2>
            <form method="post">
                <label for="organization_id">Organization ID:</label>
                <input type="text" id="organization_id" name="organization_id" required value="{{ request.form.get('organization_id', '') }}">
                
                <label for="customer_name">Customer Name:</label>
                <input type="text" id="customer_name" name="customer_name" value="{{ request.form.get('customer_name', '') }}">
                
                <label for="supplier_id">Supplier ID:</label>
                <input type="text" id="supplier_id" name="supplier_id" required value="{{ request.form.get('supplier_id', '') }}">
                
                <label for="supplier_name">Supplier Name:</label>
                <input type="text" id="supplier_name" name="supplier_name" value="{{ request.form.get('supplier_name', '') }}">
                
                <label for="country">Country:</label>
                <input type="text" id="country" name="country" value="{{ request.form.get('country', '') }}">
                
                <label for="order_created_date">Order Created Date (YYYY-MM-DD):</label>
                <input type="text" id="order_created_date" name="order_created_date" pattern="\d{4}-\d{2}-\d{2}" placeholder="YYYY-MM-DD" required value="{{ request.form.get('order_created_date', '') }}">
                
                <label for="ship_to_address_line_1">Ship to Address Line 1:</label>
                <input type="text" id="ship_to_address_line_1" name="ship_to_address_line_1" value="{{ request.form.get('ship_to_address_line_1', '') }}">
                
                <label for="ship_to_city">Ship to City:</label>
                <input type="text" id="ship_to_city" name="ship_to_city" value="{{ request.form.get('ship_to_city', '') }}">
                
                <label for="ship_to_region">Ship to Region:</label>
                <input type="text" id="ship_to_region" name="ship_to_region" value="{{ request.form.get('ship_to_region', '') }}">
                
                <label for="ship_to_country">Ship to Country:</label>
                <input type="text" id="ship_to_country" name="ship_to_country"  value="{{ request.form.get('ship_to_country', '') }}">
                
                <label for="quotation_number">Quotation Number:</label>
                <input type="text" id="quotation_number" name="quotation_number" value="{{ request.form.get('quotation_number', '') }}">
                
                <input type="submit" value="Predict">
            </form>
        </div>

        <!-- Results Section -->
        <div class="result-container {% if not predicted_cost %}hidden{% endif %}">
            <h2>Prediction Results</h2>
            {% if predicted_cost %}
            <p><strong>Predicted Shipping Cost:</strong> ${{ "%.2f" % predicted_cost }}</p>
            <p><strong>Calculated Ship Fee (1.25x):</strong> ${{ "%.2f" % (predicted_cost * 1.25) }}</p>
            {% else %}
            <p>No prediction available yet. Please fill out the form.</p>
            {% endif %}
        </div>
    </div>
</body>
</html>
    '''

    if request.method == 'POST':
        data = request.form.to_dict()
        predicted_cost, ship_fee = predict_shipping_cost(data)
        return render_template_string(html_template, predicted_cost=predicted_cost, ship_fee=ship_fee)
    return render_template_string(html_template, predicted_cost=None, ship_fee=None)


if __name__ == '__main__':
    app.run()
