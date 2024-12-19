from flask import Flask, request, jsonify, render_template_string
import requests
from abacusai import ApiClient
import webbrowser
from threading import Timer

app = Flask(__name__)

# Abacus AI configuration
api_key = 's2_771c05ba79d349f3ae6b62bbef3217ca'
deployment_id = 'bcc79e06e'
deployment_token = 'b76035fb833a4d8abae047a4b3c6bd42'

# Initialize the API client
client = ApiClient(api_key)

 # Dummy data for customers and suppliers
CUSTOMER_NAMES = []  
SUPPLIER_NAMES = []


# Function to fetch supplier names from Abacus AI
def get_customer_names_from_abacus():
    try:
        customer_name_query = """
        SELECT DISTINCT name as customer_name
        FROM gold_customers
        """
        # Execute the query and get the result as a DataFrame
        result = client.execute_feature_group_sql(customer_name_query)
        
        # Extract the names and clean them
        return [customer_name.strip() for customer_name in result['customer_name'].tolist() if isinstance(customer_name, str) and customer_name.strip()]
    except Exception as e:
        print(f"Error fetching customer names: {e}")
        return []

# Function to fetch supplier names from Abacus AI
def get_supplier_names_from_abacus():
    try:
        supplier_name_query = """
        SELECT DISTINCT name
        FROM gold_suppliers
        """
        # Execute the query and get the result as a DataFrame
        result = client.execute_feature_group_sql(supplier_name_query)
        
        # Extract the names and clean them
        return [name.strip() for name in result['name'].tolist() if isinstance(name, str) and name.strip()]
    except Exception as e:
        print(f"Error fetching supplier names: {e}")
        return []

# Fetch and update supplier names
CUSTOMER_NAMES = get_customer_names_from_abacus()
SUPPLIER_NAMES = get_supplier_names_from_abacus()

# Function to predict shipping cost
def predict_shipping_cost(data):
    try:
        result = client.predict(
            deployment_token=deployment_token,
            deployment_id=deployment_id,
            query_data=data
        )
        return result
    except Exception as e:
        print(f"Error predicting shipping cost: {e}")
        return None

# Endpoint for dynamic customer name suggestions
@app.route('/autocomplete/customers', methods=['GET'])
def autocomplete_customers():
    query = request.args.get('q', '').lower()
    suggestions = [name for name in CUSTOMER_NAMES if query in name.lower()]
    return jsonify(suggestions)

# Endpoint for dynamic supplier name suggestions
@app.route('/autocomplete/suppliers', methods=['GET'])
def autocomplete_suppliers():
    query = request.args.get('q', '').lower()
    suggestions = [name for name in SUPPLIER_NAMES if query in name.lower()]
    return jsonify(suggestions)

# Main route
@app.route('/', methods=['GET', 'POST'])
def index():
    shipping_fee = None
    shipping_cost = None

    if request.method == 'POST':
        customer_name = request.form['customer_name']
        supplier_name = request.form['supplier_name']
        supplier_country = request.form['supplier_country']
        order_created_date = request.form['order_created_date']
        ship_to_address_line_1 = request.form['ship_to_address_line_1']
        ship_to_city = request.form['ship_to_city']
        ship_to_region = request.form['ship_to_region']
        ship_to_country = request.form['ship_to_country']
        quotation_number = request.form['quotation_number']

        data = {
            "customer_name": customer_name,
            "supplier_name": supplier_name,
            "supplier_country": supplier_country,
            "transaction_type": "reseller",
            "order_purchase_type": "quote",
            "order_created_date": order_created_date,
             "ship_to_address_line_1": ship_to_address_line_1,
             "ship_to_city": ship_to_city,
             "ship_to_region": ship_to_region,
             "ship_to_country": ship_to_country,
             "quotation_number": quotation_number
            

            
        }

        prediction_result = predict_shipping_cost(data)

        if prediction_result:
            shipping_cost = round(prediction_result.get('ship_cost_in_lc', 0),2)
            shipping_fee = round(1.25 * shipping_cost,2)
            

    # Inline HTML template
    template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Shipping Fee Prediction</title>
        <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
        <style>
            .autocomplete-suggestions {
                border: 1px solid #ccc;
                max-height: 150px;
                overflow-y: auto;
                position: absolute;
                z-index: 1000;
                background-color: white;
                width: calc(100% - 20px);
            }
            .autocomplete-suggestion {
                padding: 8px;
                cursor: pointer;
            }
            .autocomplete-suggestion:hover {
                background-color: #f0f0f0;
            }
        </style>
    </head>
    <body>
        <h1>Shipping Fee Prediction</h1>

        <form method="POST">
            <label for="customer_name">Customer Name:</label>
            <input type="text" id="customer_name" name="customer_name" autocomplete="off" required>
            <div id="customer_name_suggestions" class="autocomplete-suggestions"></div>
            <br><br>

            <label for="supplier_name">Supplier Name:</label>
            <input type="text" id="supplier_name" name="supplier_name" autocomplete="off" required>
            <div id="supplier_name_suggestions" class="autocomplete-suggestions"></div>
            <br><br>

            <label for="supplier_country">Supplier Country:</label>
            <select name="supplier_country" id="supplier_country" required>
                <option value="" disabled selected>Select a country</option>
                <option value="GB">GB</option>
                <option value="US">US</option>
                <option value="DE">DE</option>
                <option value="BE">BE</option>
                <option value="FR">FR</option>
            </select>
            <br><br>

            <label for="order_created_date">Order Created Date:</label>
            <input type="date" id="order_created_date" name="order_created_date">
            <script>
                // Automatically set today's date as the default
                window.onload = function() {
                    const today = new Date().toISOString().split('T')[0];
                    document.getElementById('order_created_date').value = today;
                };
            </script>
            <br><br>

            <label for="ship_to_address_line_1">Ship To Address Line 1 (Optional):</label>
            <input type="text" id="ship_to_address_line_1" name="ship_to_address_line_1" placeholder="Optional">
            <br><br>

            <label for="ship_to_city">Ship To City (Optional):</label>
            <input type="text" id="ship_to_city" name="ship_to_city" placeholder="Optional">
            <br><br>

            <label for="ship_to_region">Ship To Region (Optional):</label>
            <input type="text" id="ship_to_region" name="ship_to_region" placeholder="Optional">
            <br><br>

            <label for="ship_to_country">Ship To Country (Optional):</label>
            <input type="text" id="ship_to_country" name="ship_to_country" placeholder="Optional">
            <br><br>

            <label for="quotation_number">Quotation Number (Optional):</label>
            <input type="text" id="quotation_number" name="quotation_number" placeholder="Optional">
            <br><br>

            <button type="submit">Submit</button>
        </form>

        {% if shipping_fee is not none %}
            <h2>Shipping Fee Prediction:</h2>
            <p>Shipping Cost: ${{ shipping_cost }}</p>
            <p>Calculated Shipping Fee: ${{ shipping_fee }}</p>
        {% endif %}

        <script>
            // Autocomplete for Customer Name
            $("#customer_name").on("input", function() {
                let query = $(this).val();
                if (query.length > 0) {
                    $.get('/autocomplete/customers', { q: query }, function(data) {
                        let suggestions = data.map(name => `<div class="autocomplete-suggestion">${name}</div>`).join('');
                        $("#customer_name_suggestions").html(suggestions).show();
                    });
                } else {
                    $("#customer_name_suggestions").hide();
                }
            });

            // Select suggestion for Customer Name
            $(document).on("click", "#customer_name_suggestions .autocomplete-suggestion", function() {
                $("#customer_name").val($(this).text());
                $("#customer_name_suggestions").hide();
            });

            // Autocomplete for Supplier Name
            $("#supplier_name").on("input", function() {
                let query = $(this).val();
                if (query.length > 0) {
                    $.get('/autocomplete/suppliers', { q: query }, function(data) {
                        let suggestions = data.map(name => `<div class="autocomplete-suggestion">${name}</div>`).join('');
                        $("#supplier_name_suggestions").html(suggestions).show();
                    });
                } else {
                    $("#supplier_name_suggestions").hide();
                }
            });

            // Select suggestion for Supplier Name
            $(document).on("click", "#supplier_name_suggestions .autocomplete-suggestion", function() {
                $("#supplier_name").val($(this).text());
                $("#supplier_name_suggestions").hide();
            });

            // Hide suggestions when clicking outside
            $(document).on("click", function(e) {
                if (!$(e.target).closest("#customer_name, #customer_name_suggestions").length) {
                    $("#customer_name_suggestions").hide();
                }
                if (!$(e.target).closest("#supplier_name, #supplier_name_suggestions").length) {
                    $("#supplier_name_suggestions").hide();
                }
            });
        </script>
    </body>
    </html>
    """
    return render_template_string(template, shipping_fee=shipping_fee, shipping_cost=shipping_cost)

if __name__ == '__main__':
    app.run()


