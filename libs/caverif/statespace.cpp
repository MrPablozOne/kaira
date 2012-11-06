
#include "statespace.h"
#include <vector>

extern CaNetDef **defs;
extern int defs_count;
extern int ca_process_count;

using namespace cass;

bool write_dot = false;

static void args_callback(char c, char *optarg, void *data)
{
	if (c == 'V') {
		if (!strcmp(optarg, "dot")) {
			write_dot = true;
			return;
		}
		fprintf(stderr, "Invalid argument in -V\n");
		exit(1);
	}
}

void cass::init(int argc, char **argv, std::vector<CaParameter*> &parameters)
{
	ca_init(argc, argv, parameters, "V:", args_callback);
}

Node::Node(CaNetDef *net_def)
{
	nets = new Net*[ca_process_count];
	packets = new std::deque<Packet>[ca_process_count];
	for (int i = 0; i < ca_process_count; i++) {
		Thread thread(packets, i, 0);
		nets[i] = (Net*) net_def->spawn(&thread);
	}
}

Node::Node()
{
	nets = new Net*[ca_process_count];
	packets = new std::deque<Packet>[ca_process_count];
}

Node::Node(const std::vector<TransitionActivation> & activations, std::deque<Packet> *packets)
	: activations(activations)
{
	nets = new Net*[ca_process_count];
	this->packets = new std::deque<Packet>[ca_process_count];
	for (int t = 0; t < ca_process_count; t++) {
		this->packets[t] = packets[t];
	}
}

Node::~Node()
{
	delete [] nets;
	delete [] packets;
}

void Node::generate(Core *core)
{
	CaNetDef *def = core->get_net_def();
	const std::vector<CaTransitionDef*> &transitions =
		def->get_transition_defs();
	int transitions_count = def->get_transitions_count();

	/* Fire transitions */
	for (int p = 0; p < ca_process_count; p++) {
		Node *node = NULL;
		for (int i = 0; i < transitions_count; i++) {
			if (node == NULL) {
				node = copy();
			}
			Net *net = node->nets[p];
			Thread thread(node->packets, p, 1);
			void *data = transitions[i]->fire_phase1(&thread, net);
			if (data) {
				TransitionActivation activation;
				activation.data = data;
				activation.transition_def = transitions[i];
				activation.process_id = p;
				activation.thread_id = 0;
				node->activations.push_back(activation);
				Node *n = core->add_node(node);
				nexts.push_back(n);
				node = NULL;
			}
		}
	}

	/* Finish transitions */
	std::vector<TransitionActivation>::iterator i;
	int p = 0;
	for (i = activations.begin(); i != activations.end(); i++, p++)
	{
		Node *node = copy();
		node->activations.erase(node->activations.begin() + p);
		Net *net = node->nets[i->process_id];
		Thread thread(node->packets, i->process_id, i->thread_id);
		i->transition_def->fire_phase2(&thread, net, i->data);
		Node *n = core->add_node(node);
		nexts.push_back(n);
	}

	/* Receive packets */
	for (int p = 0; p < ca_process_count; p++) {
		if (packets[p].empty()) {
			continue;
		}
		Node *node = copy();
		Packet packet = node->packets[p].front();
		node->packets[p].pop_front();
		CaTokens *tokens = (CaTokens *) packet.data;
		CaUnpacker unpacker(tokens + 1);
		Net *net = node->nets[p];
		int place_index = tokens->place_index;
		int tokens_count = tokens->tokens_count;
		for (int t = 0; t < tokens_count; t++) {
			net->receive(place_index, unpacker);
		}
		Node *n = core->add_node(node);
		nexts.push_back(n);
	}
}

Node* Node::copy()
{
	Node *node = new Node(activations, packets);
	for (int i = 0; i < ca_process_count; i++) {
		node->nets[i] = nets[i]->copy();
	}
	return node;
}

size_t Node::state_hash() const {
	size_t h = activations.size();
	std::vector<TransitionActivation>::const_iterator i;

	/* For activations we have to use commutative hashing ! */
	for (i = activations.begin(); i != activations.end(); i++)
	{
		size_t v = (size_t) i->transition_def;
		v += (i->process_id << 16) + i->thread_id;
		v ^= i->transition_def->binding_hash(i->data);
		h ^= v;
	}

	for (int t = 0; t < ca_process_count; t++) {
		h += nets[t]->hash();
		h += h << 10;
		h ^= h >> 6;
		std::deque<Packet>::const_iterator i;
		for (i = packets[t].begin(); i != packets[t].end(); i++) {
			h = ca_hash(i->data, i->size, h);
		}
	}
	return h;
}

bool Node::state_equals(const Node &node) const
{
	if (activations.size() != node.activations.size()) {
		return false;
	}
	for (int i = 0; i < ca_process_count; i++) {
		if (packets[i].size() != node.packets[i].size()) {
			return false;
		}
	}

	std::vector<TransitionActivation>::const_iterator i1;
	std::vector<TransitionActivation>::const_iterator i2;
	for (i1 = node.activations.begin(); i1 != node.activations.end(); i1++) {
		for (i2 = activations.begin(); i2 != activations.end(); i2++) {
			if (i1->transition_def == i2->transition_def &&
				i1->process_id == i2->process_id &&
				i1->thread_id == i2->thread_id &&
				i1->transition_def->binding_equality(i1->data, i2->data))
			{
				break;
			}
		}
		if (i2 == activations.end())
			return false;
	}

	for (int i = 0; i < ca_process_count; i++) {
		std::deque<Packet>::const_iterator p1 = packets[i].begin();
		std::deque<Packet>::const_iterator p2 = node.packets[i].begin();
        for (; p1 != packets[i].end(); p1++, p2++) {
			if (p1->size != p2->size || memcmp(p1->data, p2->data, p1->size)) {
				return false;
			}
		}
	}

	for (int i = 0; i < ca_process_count; i++) {
		if (!nets[i]->is_equal(*node.nets[i]))
			return false;
	}
	return true;
}

Core::Core() : initial_node(NULL)
{
}

Core::~Core()
{
}

void Core::generate()
{
	net_def = defs[0]; // Take first definition
	initial_node = new Node(net_def);
	add_node(initial_node);
	int count = 0;
	do {
		count++;
		if (count % 1000 == 0) {
			fprintf(stderr, "Nodes %i\n", count);
		}
		Node *node = not_processed.top();
		not_processed.pop();
		node->generate(this);
	} while (!not_processed.empty());
}

void Core::write_dot_file(const std::string &filename)
{
	FILE *f = fopen(filename.c_str(), "w");

	fprintf(f, "digraph X {\n");
	google::sparse_hash_set<Node*,
							NodeStateHash,
							NodeStateEq>::const_iterator it;
	for (it = nodes.begin(); it != nodes.end(); it++)
	{
		Node *node = *it;
		const std::vector<Node*> &nexts = node->get_nexts();
		if (node == initial_node) {
			fprintf(f, "S%p [style=filled, label=%i]\n",
				node, node->get_activations().size());
		} else {
			fprintf(f, "S%p [label=%i]\n",
				node, node->get_activations().size());
		}
		for (size_t i = 0; i < nexts.size(); i++) {
			fprintf(f, "S%p -> S%p\n", node, nexts[i]);
		}
	}
	fprintf(f, "}\n");

	fclose(f);
}

void Core::postprocess()
{
	if (write_dot) {
		write_dot_file("statespace.dot");
	}
}

Node * Core::add_node(Node *node)
{
	Node *n = get_node(node);
	if (n == NULL) {
		nodes.insert(node);
		not_processed.push(node);
		return node;
	} else {
		delete node;
		return n;
	}
}

bool Core::is_known_node(Node *node) const
{
	return nodes.find(node) != nodes.end();
}

Node * Core::get_node(Node *node) const
{
	google::sparse_hash_set<Node*,
							NodeStateHash,
							NodeStateEq>::const_iterator it;
	it = nodes.find(node);
	if (it == nodes.end())
		return NULL;
	else
		return *it;
}

int Thread::get_process_count() const
{
	return ca_process_count;
}

void Thread::multisend_multicast(const std::vector<int> &targets,
								 CaNetBase *net,
								 int place_index,
								 int tokens_count,
								 const CaPacker &packer)
{
	std::vector<int>::const_iterator i;
	CaTokens *data = (CaTokens*) packer.get_buffer();
	data->place_index = place_index;
	data->tokens_count = tokens_count;
	Packet packet;
	packet.data = data;
	packet.size = packer.get_size();
	for (i = targets.begin(); i != targets.end(); i++) {
		int target = *i;
		if(target < 0 || target >= ca_process_count) {
			fprintf(stderr,
					"Net sends %i token(s) to invalid process id %i (valid ids: [0 .. %i])\n",
					tokens_count, target, ca_process_count - 1);
			exit(1);
		}
		packets[target].push_back(packet);
	}
}
