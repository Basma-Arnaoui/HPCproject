import dash
from dash import html, dcc, Output, Input, State
import paramiko

app = dash.Dash(__name__, suppress_callback_exceptions=True)

list_of_nodes = [f"node{i:02}" for i in range(1, 18)] + ["visu01"]

app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    html.Div(id='page-content'),
    dcc.Input(id='username', type='text', placeholder='Username', style={'display': 'none'}),
    dcc.Input(id='password', type='password', placeholder='Password', style={'display': 'none'})
])

# Define the login layout
def login_layout():
    return html.Div([
        html.H2('Login to SimLab Cluster'),
        dcc.Input(id='login-username', type='text', placeholder='Username'),
        dcc.Input(id='login-password', type='password', placeholder='Password'),
        html.Button('Login', id='login-button', n_clicks=0),
        html.Div(id='login-output')
    ])

def node_page_layout():
    return html.Div([
        html.H3('Node Dashboard'),
        dcc.Dropdown(
            id='node-selector',
            options=[{'label': node, 'value': node} for node in list_of_nodes],
            value=list_of_nodes[0]
        ),
        html.Div(id='node-details')
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
     Output('password', 'value')],
    Input('login-button', 'n_clicks'),
    [State('login-username', 'value'), State('login-password', 'value')])
def login(n_clicks, login_username, login_password):
    if n_clicks and login_username and login_password:
        if authenticate(login_username, login_password):
            return '/nodes', login_username, login_password
        else:
            return '/login?error=true', dash.no_update, dash.no_update
    return dash.no_update, dash.no_update, dash.no_update

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

        # Format and return node details for the dashboard
        details = [html.P(line) for line in node_info.split('\n') if line.strip()]
        return details if details else html.P("No details available for the selected node.")

    except Exception as e:
        return html.Div(f"Error fetching details for node {selected_node}: {str(e)}")

if __name__ == '__main__':
    app.run_server(debug=True)
