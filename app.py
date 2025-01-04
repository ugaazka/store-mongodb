from flask import Flask, render_template, request, redirect, url_for, session
from pymongo import MongoClient
from datetime import datetime
from bson.objectid import ObjectId
from flask import flash
from bson.objectid import ObjectId
from bson.objectid import ObjectId 
# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# MongoDB client setup
client = MongoClient("mongodb://localhost:27017/")
db = client.store_mangement

# Routes
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        data = request.form
        try:
            db.users.insert_one({
                "name": data['name'],
                "email": data['email'],
                "password": data['password'],  # In production, hash the password!
                "role": data['role']  # Capture the role from the form
            })
            flash('Registration successful!', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            flash(f'Error during registration: {str(e)}', 'danger')
            return redirect(url_for('register'))
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.form
        user = db.users.find_one({"email": data['email']})
        if user and user['password'] == data['password']:
            session['user'] = {
                "id": str(user['_id']),
                "role": user['role'],  # Include the user's role in the session
                "name": user['name']
            }
            if user['role'] == 'admin':
                return redirect(url_for('admin_dashboard'))  # Redirect admins to admin dashboard
            elif user['role'] == 'manager':
                return redirect(url_for('dashboard'))  # Redirect managers
            else:
                return redirect(url_for('dashboard'))  # Default for regular users
        flash('Invalid credentials!', 'danger')
        return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/admin', methods=['GET'])
def admin_dashboard():
    if 'user' in session and session['user']['role'] == 'admin':
        return render_template('admin_dashboard.html')
    flash('Unauthorized access!', 'danger')
    return redirect(url_for('login'))

@app.route('/view_users', methods=['GET'])
def view_users():
    if 'user' in session and session['user']['role'] == 'admin':
        users = list(db.users.find({}, {"name": 1, "email": 1, "role": 1}))
        return render_template('view_users.html', users=users)
    flash('Unauthorized access!', 'danger')
    return redirect(url_for('login'))


@app.route('/dashboard')
def dashboard():
    if 'user' in session:
        user = session['user']
        if user['role'] == 'admin':
            return render_template('admin_dashboard.html', user=user)
        return render_template('user_dashboard.html', user=user)
    return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/shop', methods=['GET'])
def shop():
    if 'user' in session:
        categories = list(db.categories.find())
        selected_category = request.args.get('category')
        if selected_category:
            products = list(db.products.find({"category_id": selected_category}))
        else:
            products = list(db.products.find())
        return render_template('shop.html', products=products, categories=categories, user=session['user'])
    return redirect(url_for('login'))

@app.route('/add_purchase', methods=['POST'])
def add_purchase():
    if 'user' in session:
        try:
            data = request.form
            purchase = {
                "order_id": data.get('order_id', "N/A"),  # Xogta order_id haddii uu jiro
                "product_name": data['product_name'],
                "quantity": int(data['quantity']),
                "total_price": float(data['total_price']),
                "purchase_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

            # Check haddii purchases hore loo sameeyey
            if 'purchases' not in session:
                session['purchases'] = []

            # Ku dar xogta cusub ee purchases
            session['purchases'].append(purchase)
            flash('Purchase added successfully!', 'success')
        except Exception as e:
            flash(f'Error adding purchase: {str(e)}', 'danger')
        return redirect(url_for('purchased_items'))
    return redirect(url_for('login'))

@app.route('/purchased_items', methods=['GET'])
def purchased_items():
    if 'user' in session:
        # Soo hel purchases ka session
        purchases = session.get('purchases', [])
        return render_template('purchased_items.html', purchases=purchases)
    return redirect(url_for('login'))


@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    if 'user' in session:
        product_id = request.form['product_id']
        quantity = int(request.form['quantity'])

        product = db.products.find_one({"name": product_id})

        if not product or product['stock'] < quantity:
            return "Not enough stock available.", 400

        cart = session.get('cart', [])
        cart.append({"product_id": product_id, "quantity": quantity, "price": product['price']})
        session['cart'] = cart
        return redirect(url_for('view_cart'))
    return redirect(url_for('login'))

@app.route('/view_cart')
def view_cart():
    if 'user' in session:
        cart = session.get('cart', [])
        total_price = sum(item['price'] * item['quantity'] for item in cart)
        return render_template('cart.html', cart=cart, total_price=total_price, user=session['user'])
    return redirect(url_for('login'))


@app.route('/checkout', methods=['POST'])
def checkout():
    if 'user' in session:
        cart = session.get('cart', [])
        if not cart:
            flash('Your cart is empty!', 'warning')
            return redirect(url_for('shop'))

        # Save purchases in the session instead of the database
        if 'purchases' not in session:
            session['purchases'] = []

        for item in cart:
            purchase = {
                "product_name": item['product_id'],
                "quantity": item['quantity'],
                "total_price": item['price'] * item['quantity'],
                "purchase_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            session['purchases'].append(purchase)

        # Clear cart
        session['cart'] = []
        flash('Purchase completed successfully!', 'success')
        return redirect(url_for('purchased_items'))
    return redirect(url_for('login'))

@app.route('/suppliers', methods=['GET'])
def suppliers():
    if 'user' in session and session['user']['role'] == 'admin':
        suppliers = list(db.suppliers.find())
        return render_template('suppliers.html', suppliers=suppliers)
    return redirect(url_for('login'))

@app.route('/add_supplier', methods=['POST'])
def add_supplier():
    if 'user' in session and session['user']['role'] == 'admin':
        try:
            supplier_data = {
                "supplier_id": request.form['supplier_id'],
                "name": request.form['name'],
                "contact_person": request.form['contact_person'],
                "phone": request.form['phone'],
                "email": request.form['email'],
                "products_supplied": request.form['products_supplied'].split(', ')
            }
            db.suppliers.insert_one(supplier_data)
            flash('Supplier added successfully!', 'success')
        except Exception as e:
            flash(f'Error adding supplier: {str(e)}', 'danger')
        return redirect(url_for('suppliers'))
    return redirect(url_for('login'))


@app.route('/delete_supplier', methods=['POST'])
def delete_supplier():
    if 'user' in session and session['user']['role'] == 'admin':
        try:
            supplier_id = request.form['supplier_id']
            db.suppliers.delete_one({"_id": ObjectId(supplier_id)})
            flash('Supplier deleted successfully!', 'success')
        except Exception as e:
            flash(f'Error deleting supplier: {str(e)}', 'danger')
        return redirect(url_for('suppliers'))
    return redirect(url_for('login'))


@app.route('/inventorys', methods=['GET'])
def inventorys():
    if 'user' in session:
        inventory = list(db.inventorys.find())
        return render_template('inventorys.html', inventory=inventory)
    return redirect(url_for('login'))

@app.route('/add_inventorys', methods=['POST'])
def add_inventorys():
    if 'user' in session and session['user']['role'] == 'admin':
        data = request.form
        try:
            db.inventorys.insert_one({
                "product_id": data['product_id'],
                "stock_level": int(data['stock_level']),
            })
            flash('Inventory item added successfully!', 'success')
        except Exception as e:
            flash(f'Error adding inventory item: {str(e)}', 'danger')
        return redirect(url_for('inventorys'))
    return redirect(url_for('login'))

@app.route('/delete_inventorys', methods=['POST'])
def delete_inventorys():
    if 'user' in session and session['user']['role'] == 'admin':
        inventory_id = request.form['inventory_id']
        try:
            db.inventorys.delete_one({"_id": ObjectId(inventory_id)})
            flash('Inventory item deleted successfully!', 'success')
        except Exception as e:
            flash(f'Error deleting inventory item: {str(e)}', 'danger')
        return redirect(url_for('inventorys'))
    return redirect(url_for('login'))

@app.route('/catogerys', methods=['GET'])
def catogerys():
    if 'user' in session:
        categories = list(db.catogerys.find())
        return render_template('catogerys.html', categories=categories)
    return redirect(url_for('login'))

@app.route('/add_category', methods=['POST'])
def add_category():
    if 'user' in session and session['user']['role'] == 'admin':
        data = request.form
        try:
            db.catogerys.insert_one({
                "name": data['name'],
                "description": data['description']
            })
            flash('Category added successfully!', 'success')  # Flash success message
        except Exception as e:
            flash(f'Error adding category: {str(e)}', 'danger')  # Flash error message
       
    return redirect(url_for('login'))




@app.route('/delete_category', methods=['POST'])
def delete_category():
    if 'user' in session and session['user']['role'] == 'admin':
        category_id = request.form['category_id']
        try:
            db.catogeys.delete_one({"_id": ObjectId(category_id)})
            flash('Category deleted successfully!', 'success')  # Flash success message
        except Exception as e:
            flash(f'Error deleting category: {str(e)}', 'danger')  # Flash error message
       
    return redirect(url_for('login'))


@app.route('/sales', methods=['GET'])
def sales():
    if 'user' in session:
        sales = list(db.sales.find())
        return render_template('sales.html', sales=sales)
    return redirect(url_for('login'))

@app.route('/add_sales', methods=['POST'])
def add_sales():
    if 'user' in session and session['user']['role'] == 'admin':
        try:
            sale_data = {
                "order_id": request.form['order_id'],
                "user_id": request.form['user_id'],
                "total_price": float(request.form['total_price']),
                "sale_date": datetime.strptime(request.form['sale_date'], "%Y-%m-%d").isoformat()
            }
            db.sales.insert_one(sale_data)
            flash('Sale added successfully!', 'success')
        except Exception as e:
            flash(f'Error adding sale: {str(e)}', 'danger')
        return redirect(url_for('sales'))
    return redirect(url_for('login'))

@app.route('/delete_sales', methods=['POST'])
def delete_sales():
    if 'user' in session and session['user']['role'] == 'admin':
        try:
            sale_id = request.form['sale_id']
            db.sales.delete_one({"_id": ObjectId(sale_id)})
            flash('Sale deleted successfully!', 'success')
        except Exception as e:
            flash(f'Error deleting sale: {str(e)}', 'danger')
        return redirect(url_for('sales'))
    return redirect(url_for('login'))



@app.route('/system_logs', methods=['GET'])
def system_logs():
    if 'user' in session and session['user']['role'] == 'admin':  # Ensure only admin sees logs
        try:
            # Fetch logs from the 'system_logs' collection
            system_logs = list(db.system_logs.find())
            
            # Ensure system_logs contains documents
            if not system_logs:
                flash("No logs found in the system.", "warning")
            
            # Pass logs to the template
            return render_template('system_logs.html', system_logs=system_logs)
        except Exception as e:
            flash(f"Error fetching system logs: {str(e)}", "danger")
            return redirect(url_for('dashboard'))  # Redirect to dashboard on error
    return redirect(url_for('login'))

@app.route('/add_system_log', methods=['POST'])
def add_system_log():
    if 'user' in session and session['user']['role'] == 'admin':
        try:
            log_data = {
                "event": request.form['event'],
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            db.system_logs.insert_one(log_data)
            flash('Log added successfully!', 'success')
        except Exception as e:
            flash(f'Error adding log: {str(e)}', 'danger')
        return redirect(url_for('system_logs'))
    return redirect(url_for('login'))


@app.route('/delete_system_log', methods=['POST'])
def delete_system_log():
    if 'user' in session and session['user']['role'] == 'admin':
        try:
            log_id = request.form['log_id']
            db.system_logs.delete_one({"_id": ObjectId(log_id)})
            flash('Log deleted successfully!', 'success')
        except Exception as e:
            flash(f'Error deleting log: {str(e)}', 'danger')
        return redirect(url_for('system_logs'))
    return redirect(url_for('login'))


@app.route('/products', methods=['GET', 'POST'])
def manage_products():
    if 'user' in session and session['user']['role'] == 'admin':
        if request.method == 'POST':
            # Handle the product addition form submission
            data = request.form
            try:
                db.products.insert_one({
                    "name": data['name'],
                    "price": float(data['price']),
                    "category_id": data['category_id'],
                    "stock": int(data['stock']),
                })
                flash('Product added successfully!', 'success')
            except Exception as e:
                flash(f'Error adding product: {str(e)}', 'danger')
            return redirect(url_for('manage_products'))

        # Handle GET request to display the product list
        products = list(db.products.find())
        return render_template('products.html', products=products, user=session['user'])
    return redirect(url_for('login'))



@app.route('/delete_product', methods=['POST'])
def delete_product():
    if 'user' in session and session['user']['role'] == 'admin':
        product_id = request.form['product_id']
        try:
            db.products.delete_one({"_id": ObjectId(product_id)})  # Use ObjectId for the `_id` field
            flash('Product deleted successfully!', 'success')  # Use flash for success messages
        except Exception as e:
            flash(f'Error deleting product: {str(e)}', 'danger')  # Handle potential errors
        return redirect(url_for('manage_products'))
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
