"""
Some functions to plot specifically weights and activations of Lissom modules
"""

import numpy as np
from torchvision import utils as vutils

from pylissom.nn.modules import named_apply
from pylissom.nn.modules.linear import UnnormalizedDifferenceOfGaussiansLinear
from pylissom.nn.modules.lissom import DifferenceOfGaussiansLinear
from pylissom.utils.plotting.matrix import plot_dict_matrices
# from tensorboard import SummaryWriter
from pylissom.utils.plotting.matrix import tensor_to_numpy_matrix

logdir = 'runs'
log_interval = 10


# def generate_images(self, input, output, prefix=''):
#     if self.batch_idx % log_interval != 0:
#         self.batch_idx += 1
#         return
#     writer = get_writer(self.training, self.epoch, prefix)
#
#     for name, mat in self.weights + [('activation', self.activation.t()), ('input', self.input.t())]:
#         if isinstance(mat, torch.autograd.Variable):
#             mat = mat.data
#         if 'weights' in name and self.sparse:
#             mat = mat.to_dense()
#         if isinstance(self, LGNLayer) and 'weights' in name:
#             range = (-1, 1)
#         else:
#             range = (0, 1)
#         image = images_matrix(mat, range)
#         title = self.name + '_' + name
#         writer.add_image(title, image, self.batch_idx)
#     writer.close()
#     self.batch_idx += 1
#
#
# def get_writer(train, epoch, prefix):
#     log_path = logdir \
#                + ('/' + prefix + '/' if prefix != '' else '') \
#                + ('/train/' if train else '/test/') \
#                + 'epoch_' + str(epoch)
#     writer = SummaryWriter(log_dir=log_path)
#     return writer


def images_matrix(matrix, range_interval=None):
    out_features = matrix.size()[0]
    in_features = matrix.size()[1]
    weights_shape = (int(np.sqrt(in_features)), int(np.sqrt(in_features)))
    reshaped_weights = matrix.contiguous().view((out_features, 1) + weights_shape)
    im = vutils.make_grid(reshaped_weights, normalize=True, nrow=int(np.sqrt(reshaped_weights.size()[0])), range=range_interval)
        # ,
        #                   pad_value=0.5 if range is not None and range[0] >= 0 else 0)
    return im


def weights_to_numpy_matrix(weights, values_range):
    grid = images_matrix(weights, values_range)
    grid = grid.cpu() if grid.is_cuda else grid
    return np.transpose(grid.numpy(), (1, 2, 0))


def plot_layer_weights(layer, use_range=True, recursive=False, prefix=''):
    """Assumes layer parameters are weights and plots them
    Args:
        layer: Plots weights (parameters) of this layer
        use_range: Normalize the image values between (0, 1) or (-1, 1) if layer is :py:class:`pylissom.nn.modules.lissom.DifferenceOfGaussiansLinear`
        recursive: Plot weights of children modules recursively
        prefix: Title of plot
    """
    if use_range:
        values_range = (-1, 1) if isinstance(layer, DifferenceOfGaussiansLinear) \
                                  or isinstance(layer, UnnormalizedDifferenceOfGaussiansLinear) else (0, 1)
    else:
        values_range = None
    plot_dict_matrices({prefix + '.' + k: weights_to_numpy_matrix(w.data, values_range)
                        for k, w in layer.named_parameters()})
    if recursive:
        for k, c in layer.named_children():
            plot_layer_weights(c, prefix=k + '.')
    return


def simple_plot_layer_activation(layer, prefix=''):
    try:
        input_rows = int(layer.in_features ** 0.5)
        output_rows = int(layer.out_features ** 0.5)
        inp_mat = tensor_to_numpy_matrix(layer.input.data, (input_rows, input_rows))
        act_mat = tensor_to_numpy_matrix(layer.output.data, (output_rows, output_rows))
        plot_dict_matrices(dict([(prefix + '.' + 'input', inp_mat), (prefix + '.' + 'activation', act_mat)]))
    # TODO: change excpetion to more specific one
    except Exception:
        pass


def plot_layer_activation(layer, prefix=''):
    """Plots input and activation of layer and children modules recursively

    Assumes layer has input and output parameters defined (probably defined with
    :py:func:`pylissom.nn.modules.register_recursive_input_output_hook`

    Args:
        layer: Layer to plot
        prefix: Title of plot
    """
    named_apply(layer, simple_plot_layer_activation, prefix)


# def plot_cortex_activations(cortex):
#     inp_act_plots = plot_layer_activation(cortex)
#     activations = [tensor_to_numpy_matrix(act, cortex.self_shape) for act in [cortex.afferent_activation,
#                                                                               cortex.inhibitory_activation,
#                                                                               cortex.excitatory_activation]]
#     return inp_act_plots + plot_array_matrix(activations)
