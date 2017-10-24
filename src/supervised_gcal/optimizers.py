import torch
from src.supervised_gcal.cortex_layer import CortexLayer
from src.supervised_gcal.utils.functions import kill_neurons, linear_decay
from src.supervised_gcal.utils.weights import apply_circular_mask_to_weights


class CortexOptimizer(torch.optim.Optimizer):
    def __init__(self, cortex_layer):
        assert isinstance(cortex_layer, CortexLayer)
        self.cortex_layer = cortex_layer
        super(CortexOptimizer, self).__init__(cortex_layer.parameters(), {})


class SequentialOptimizer(object):
    # TODO: inherit from torch.optim.Optimizer
    def __init__(self, *optimizers):
        self.optimizers = optimizers

    def step(self):
        for opt in self.optimizers:
            opt.step()

    def zero_grad(self):
        for opt in self.optimizers:
            opt.zero_grad()


class CortexHebbian(CortexOptimizer):
    def __init__(self, cortex_layer, learning_rate):
        super(CortexHebbian, self).__init__(cortex_layer)
        self.learning_rate = learning_rate

    def step(self, **kwargs):
        self.hebbian_learning(self.cortex_layer.weights, self.cortex_layer.input, self.cortex_layer.activation,
                              self.learning_rate, self.cortex_layer.radius)

    @staticmethod
    def hebbian_learning(weights, input, output, learning_rate, radius):
        # Weight adaptation of a single neuron
        # w'_pq,ij = (w_pq,ij + alpha * input_pq * output_ij) / sum_uv (w_uv,ij + alpha * input_uv * output_ij)

        delta = learning_rate * torch.matmul(torch.t(input.data), output.data)
        weights.data.add_(delta)
        apply_circular_mask_to_weights(weights.data.t_(), radius)
        weights.data.t_()
        den = torch.norm(weights.data, p=1, dim=0)
        weights.data.div_(den)
        return


class CortexPruner(CortexOptimizer):
    def __init__(self, cortex_layer, pruning_step=2000):
        super(CortexPruner, self).__init__(cortex_layer)
        self.pruning_step = pruning_step
        self.step_counter = 1

    def step(self, **kwargs):
        if self.step_counter % self.pruning_step == 0:
            self.prune()
        self.step_counter += 1

    def prune(self):
        raise NotImplementedError


class ConnectionDeath(CortexPruner):
    def __init__(self, cortex_layer, pruning_step=2000, connection_death_threshold=1.0 / 400):
        super(ConnectionDeath, self).__init__(cortex_layer, pruning_step)
        self.connection_death_threshold = connection_death_threshold

    def prune(self):
        map(lambda w: kill_neurons(w, self.connection_death_threshold),
            [self.cortex_layer.excitatory_weights, self.cortex_layer.inhibitory_weights])


class NeighborsDecay(CortexPruner):
    def __init__(self, cortex_layer, pruning_step=2000, decay_fn=linear_decay, final_epoch=8.0):
        super(NeighborsDecay, self).__init__(cortex_layer, pruning_step)
        self.decay_fn = decay_fn
        self.final_epoch = final_epoch

    def prune(self):
        self.decay_fn(self.cortex_layer.excitatory_weights, self.cortex_layer.excitatory_radius,
                      epoch=self.cortex_layer.epoch, final_epoch=self.final_epoch)
