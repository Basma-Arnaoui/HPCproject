import dash
from dash import Dash, html, dcc, Output, Input, State
import paramiko
import re

app = dash.Dash(__name__, suppress_callback_exceptions=True)

list_of_nodes = [f"node{i:02}" for i in range(1, 18)] + ["visu01"]

# Define some common styles
common_styles = {
    'margin': '10px',
    'padding': '15px',
    'border-radius': '5px',
    'border': '1px solid #ddd',
    'background-color': '#f9f9f9'
}

login_styles = {
    'padding': '2rem',
    'background-color': 'white',  # White card for the login form
    'color': '#333',
    'width': '350px',
    'margin': 'auto',
    'position': 'absolute',
    'top': '50%',
    'left': '50%',
    'transform': 'translate(-50%, -50%)',
    'border-radius': '8px',
    'box-shadow': '0 4px 8px 0 rgba(0,0,0,0.2)',
    'display': 'flex',
    'flex-direction': 'column',
    'justify-content': 'center',
    'align-items': 'center',
}


input_styles = {
    'width': '80%',
    'padding': '10px',
    'margin': '10px 0',
    'border': '1px solid #ddd',
    'border-radius': '20px',
    'box-sizing': 'border-box'
}

button_styles = {
    'width': '80%',
    'padding': '10px',
    'border': 'none',
    'background-color': '#6a1b9a',  # Purple color for the button
    'color': 'white',
    'margin-top': '20px',
    'border-radius': '20px',
    'cursor': 'pointer',
}

page_background_style = {
    'height': '100vh',
    'width': '100%',
    'background': 'linear-gradient(to right, #7b4397, #dc2430)',  # Gradient background with purple
    'font-family': 'Arial, sans-serif'
}

app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    html.Div(id='page-content', style=common_styles),
    dcc.Input(id='username', type='text', placeholder='Username', style={'display': 'none'}),
    dcc.Input(id='password', type='password', placeholder='Password', style={'display': 'none'})
], style=page_background_style)


def login_layout():
    return html.Div([
        html.H2('Login to SimLab Cluster'),
        dcc.Input(id='login-username', type='text', placeholder='Username'),
        dcc.Input(id='login-password', type='password', placeholder='Password'),
        html.Button('Login', id='login-button', n_clicks=0),
        html.Div(id='login-output'),
        html.Div(id='alert')  # For displaying login error messages
    ], style=login_styles)


def node_page_layout():
    return html.Div([
        html.H3('Node Dashboard'),
        dcc.Dropdown(
            id='node-selector',
            options=[{'label': node, 'value': node} for node in list_of_nodes],
            value=list_of_nodes[0]
        ),
        html.Div(id='node-details', style=common_styles)
    ])

@app.callback(Output('page-content', 'children'),
              Input('url', 'pathname'))
def display_page(pathname):
    if pathname == '/nodes':
        return node_page_layout()
    else:
        return login_layout()

@app.callback(
    [Output('url', 'pathname'),
     Output('username', 'value'),
     Output('password', 'value'),
     Output('alert', 'children')],
    Input('login-button', 'n_clicks'),
    [State('login-username', 'value'), State('login-password', 'value')])
def login(n_clicks, login_username, login_password):
    if n_clicks and login_username and login_password:
        if authenticate(login_username, login_password):
            return '/nodes', login_username, login_password, ""
        else:
            return '/login', dash.no_update, dash.no_update, html.Div("Incorrect username or password", style={'color': 'red'})
    return dash.no_update, dash.no_update, dash.no_update, ""

def authenticate(username, password):
    try:
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(
            hostname='simlab-cluster.um6p.ma',
            username=username,
            password=password
        )
        ssh_client.close()
        return True
    except paramiko.AuthenticationException:
        return False
    except Exception as e:
        print(f"An error occurred: {e}")
        return False

@app.callback(
    Output('node-details', 'children'),
    [Input('node-selector', 'value')],
    [State('username', 'value'), State('password', 'value')])
def update_node_details(selected_node, username, password):
    if not username or not password:
        return html.Div("No credentials provided. Please log in again.")

    try:
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(
            hostname='simlab-cluster.um6p.ma',
            username=username,
            password=password
        )

        command = f"scontrol show node {selected_node}"
        stdin, stdout, stderr = ssh_client.exec_command(command)
        node_info = stdout.read().decode('utf-8')
        ssh_client.close()

        # Parsing data from node_info
        cpu_alloc, cpu_total, cpu_load = parse_cpu_data(node_info)
        mem_total, mem_alloc, mem_free = parse_memory_data(node_info)
        gpu_total = parse_gpu_data(node_info)  # Adjust as per your actual GPU data format

        # Visualization - CPU
        cpu_free = cpu_total - cpu_alloc
        cpu_fig = dcc.Graph(
            figure={
                'data': [{'values': [cpu_alloc, cpu_free], 'type': 'pie', 'name': 'CPU Usage',
                          'labels': ['Allocated', 'Free']}],
                'layout': {'title': 'CPU Usage'}
            }
        )

        # Visualization - Memory
        mem_fig = dcc.Graph(
            figure={
                'data': [{'values': [mem_alloc, mem_free], 'type': 'pie', 'name': 'Memory Usage',
                          'labels': ['Allocated', 'Free']}],
                'layout': {'title': 'Memory Usage'}
            }
        )

        # Visualization - GPU
        gpu_fig = dcc.Graph(
            figure={
                'data': [{'values': [gpu_total, 1], 'type': 'pie', 'name': 'GPU Usage','labels': ['Allocated', 'Free']}],  # Modify as per your data
                'layout': {'title': 'GPU Usage'}
            }
        )

        return [cpu_fig, mem_fig, gpu_fig]

    except Exception as e:
        return html.Div(f"Error fetching details for node {selected_node}: {str(e)}")

def parse_cpu_data(node_info):
    cpu_pattern = re.compile(r"CPUAlloc=(\d+) CPUErr=\d+ CPUTot=(\d+) CPULoad=([\d.]+)")
    match_cpu = cpu_pattern.search(node_info)
    if match_cpu:
        cpu_alloc, cpu_total, cpu_load_str = match_cpu.groups()
        cpu_load = float(cpu_load_str)  # CPU load can be a float
        return int(cpu_alloc), int(cpu_total), cpu_load
    return 0, 0, 0.0

def parse_memory_data(node_info):
    memory_pattern = re.compile(r"RealMemory=(\d+) AllocMem=(\d+) FreeMem=(\d+)")
    match_memory = memory_pattern.search(node_info)
    return map(int, match_memory.groups()) if match_memory else (0, 0, 0)

def parse_gpu_data(node_info):
    # Placeholder pattern - Adjust to your actual GPU data format in node_info
    gpu_pattern = re.compile(r"Gres=gpu:(\d+)")
    match_gpu = gpu_pattern.search(node_info)
    return int(match_gpu.group(1)) if match_gpu else 0

if __name__ == '__main__':
    app.run_server(debug=True)
