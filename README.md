# zellular.py

A Python SDK for interacting with the Zellular network.

## Dependencies

To use zelluar.py, you'll need to install the [MCL](https://github.com/herumi/mcl) native library. Follow these steps to install it:

```
$ sudo apt install libgmp3-dev
$ wget https://github.com/herumi/mcl/archive/refs/tags/v1.93.zip
$ unzip v1.93.zip
$ cd mcl-1.93
$ mkdir build
$ cd build
$ cmake ..
$ make
$ make install
```

## Installation

Install the zelluar.py package via pip:

```
pip install zellular
```

## Usage

### Network Architectures

Zellular supports multiple network architectures:

1. **EigenlayerNetwork**: For interacting with Zellular deployed on EigenLayer.
2. **StaticNetwork**: For local testing or proof-of-authority deployments with a fixed set of operators.

### Setting Up With EigenLayer Network

```python
from zellular import Zellular, EigenlayerNetwork

# Create the network instance
network = EigenlayerNetwork(
    subgraph_url="https://api.studio.thegraph.com/query/95922/avs-subgraph/v0.0.3",
    threshold_percent=67  # Default threshold for consensus
)

# Create the Zellular client
app_name = "simple_app"
zellular = Zellular(app_name, network)
```

### Setting Up With Static Network

```python
import json
from zellular import Zellular, StaticNetwork

# Load node data from a JSON file
with open("nodes.json") as f:
    nodes_data = json.load(f)

# Create the network instance
network = StaticNetwork(nodes_data, threshold_percent=67)

# Create the Zellular client
app_name = "simple_app"
zellular = Zellular(app_name, network)
```

### Active Operators and Gateway Selection

When initializing a Zellular client, you can optionally specify a `gateway` parameter to connect to a specific operator. If you don't provide a gateway, Zellular automatically selects a random active operator for your application:

```python
from zellular import Zellular, EigenlayerNetwork

network = EigenlayerNetwork(
    subgraph_url="https://api.studio.thegraph.com/query/95922/avs-subgraph/v0.0.3",
    threshold_percent=67
)

# Without gateway parameter - automatically selects a random active operator
zellular_auto = Zellular("simple_app", network)

# With custom gateway parameter - uses the specified operator
custom_gateway = "http://your-custom-operator:6001"
zellular_custom = Zellular("simple_app", network, gateway=custom_gateway)
```

You can also manually find operators that are actively participating in consensus for a specific app using the `get_active_operators` method:

```python
import asyncio
from pprint import pprint
from zellular import Zellular, EigenlayerNetwork

network = EigenlayerNetwork(
    subgraph_url="https://api.studio.thegraph.com/query/95922/avs-subgraph/v0.0.3",
    threshold_percent=67
)

zellular = Zellular("simple_app", network)

# Get active operators - returns operators running latest version with up-to-date consensus state
active_operators = asyncio.run(zellular.get_active_operators("simple_app"))
pprint(active_operators)

# Manually select a random active operator if needed
if active_operators:
    random_operator = active_operators[0]
    print(f"Selected operator: {random_operator.socket}")
```

Active operator selection is particularly useful when you need to:
- Find healthy nodes for your application
- Ensure you're connecting to operators running the latest version
- Select a node with an up-to-date view of the consensus state

### Posting Transactions

Zellular sequences transactions in batches. You can send a batch of transactions like this:

```python
import time
from uuid import uuid4
from zellular import Zellular, EigenlayerNetwork

network = EigenlayerNetwork(
    subgraph_url="https://api.studio.thegraph.com/query/95922/avs-subgraph/v0.0.3",
    threshold_percent=67
)

app_name = "simple_app"
zellular = Zellular(app_name, network)

t = int(time.time())
txs = [{"operation": "foo", "tx_id": str(uuid4()), "t": t} for _ in range(5)]

index = zellular.send(txs, blocking=True)
```

When setting `blocking=True`, the method waits for the batch to be sequenced and returns the index.

> [!TIP]
> You can add your app to zellular test network using:
> `curl -X POST https://www.zellular.xyz/testnet/apps -H "Content-Type: application/json" -d '{"app_name": "your-app-name"}'`


### Fetching and Verifying Transactions

Unlike reading from a traditional blockchain, where you must trust the node you're connected to, Zellular allows trustless reading of sequenced transactions. This is achieved through an aggregated BLS signature that verifies if the sequence of transaction batches is approved by the majority of Zellular nodes. The Zellular SDK abstracts the complexities of verifying these signatures, providing a simple way to constantly pull the latest finalized transaction batches:

```python
import json
from zellular import Zellular, EigenlayerNetwork

network = EigenlayerNetwork(
    subgraph_url="https://api.studio.thegraph.com/query/95922/avs-subgraph/v0.0.3",
    threshold_percent=67
)

app_name = "simple_app"
zellular = Zellular(app_name, network)

for batch, index in zellular.batches(after=0):
    txs = json.loads(batch)
    for i, tx in enumerate(txs):
        print(index, i, tx)
```
Example output:

```
app: simple_app, index: 1, result: True
app: simple_app, index: 2, result: True
583 0 {'tx_id': '7eaa...2101', 'operation': 'foo', 't': 1725363009}
583 1 {'tx_id': '5839...6f5e', 'operation': 'foo', 't': 1725363009}
583 2 {'tx_id': '0a1a...05cb', 'operation': 'foo', 't': 1725363009}
583 3 {'tx_id': '6339...cc08', 'operation': 'foo', 't': 1725363009}
583 4 {'tx_id': 'cf4a...fc19', 'operation': 'foo', 't': 1725363009}
...
```

If you want to start reading batches from the latest finalized batch rather than from the beginning, you can achieve this by specifying the `after` parameter with the latest index. Here's an example of how to do this:

```python
index = zellular.get_last_finalized()["index"]
for batch, index in zellular.batches(after=index):
    ...
```

## Testing

To test the Zellular SDK locally, you need to simulate a Zellular network environment. This is done using the [zsequencer](https://github.com/zellular-xyz/zsequencer/) repository.

### Step 1: Clone and Run the ZSequencer Simulation

Follow the instructions in the [zsequencer test section](https://github.com/zellular-xyz/zsequencer/#testing) to run a local Zellular network simulation. This includes spinning up a simulation netowrk of operator nodes:

```bash
git clone https://github.com/zellular-xyz/zsequencer.git
cd zsequencer
docker compose build
uv run -m tests.e2e.run start
```

### Step 2: Clone and Install Zellular SDK in Dev Mode

In a separate terminal:

```bash
git clone https://github.com/zellular-xyz/zellular.py.git
cd zellular.py
pip install -e .[dev]
```

### Step 3: Run the Tests

With the simulation network running, you can now run the test suite:

```bash
pytest tests/test_zellular_static.py
```