from __future__ import print_function

import argparse
import os
import shutil

import visdom
from tensorboard import SummaryWriter

import torch
import torch.nn as nn
import torch.nn.functional as F
import torchvision.utils as vutils
from src.supervised_gcal.cortex_layer import LissomCortexLayer
from src.supervised_gcal.hebbian_optimizer import LissomHebbianOptimizer
from torch.autograd import Variable
from torchvision import datasets, transforms

if os.path.exists('runs'):
    shutil.rmtree('runs')
writer = SummaryWriter()
vis = visdom.Visdom()

# Training settings
parser = argparse.ArgumentParser(description='PyTorch MNIST Example')
parser.add_argument('--batch-size', type=int, default=64, metavar='N',
                    help='input batch size for training (default: 64)')
parser.add_argument('--test-batch-size', type=int, default=1000, metavar='N',
                    help='input batch size for testing (default: 1000)')
parser.add_argument('--epochs', type=int, default=10, metavar='N',
                    help='number of epochs to train (default: 10)')
parser.add_argument('--lr', type=float, default=0.01, metavar='LR',
                    help='learning rate (default: 0.01)')
parser.add_argument('--momentum', type=float, default=0.5, metavar='M',
                    help='SGD momentum (default: 0.5)')
parser.add_argument('--no-cuda', action='store_true', default=False,
                    help='disables CUDA training')
parser.add_argument('--seed', type=int, default=1, metavar='S',
                    help='random seed (default: 1)')
parser.add_argument('--log-interval', type=int, default=10, metavar='N',
                    help='how many batches to wait before logging training status')
parser.add_argument('--ipdb', action='store_true', default=False,
                    help='activate ipdb set_trace()')
args = parser.parse_args()

if not args.ipdb:
    import ipdb

    ipdb.set_trace = lambda: 0

args.cuda = not args.no_cuda and torch.cuda.is_available()

torch.manual_seed(args.seed)
if args.cuda:
    torch.cuda.manual_seed(args.seed)

kwargs = {'num_workers': 1, 'pin_memory': True} if args.cuda else {}
train_loader = torch.utils.data.DataLoader(
    datasets.MNIST('../data', train=True, download=True,
                   transform=transforms.ToTensor()
                   ),
    batch_size=args.batch_size, shuffle=True, **kwargs)
test_loader = torch.utils.data.DataLoader(
    datasets.MNIST('../data', train=False, transform=transforms.ToTensor()),
    batch_size=args.batch_size, shuffle=True, **kwargs)


class Net(nn.Module):
    def __init__(self):
        super(Net, self).__init__()
        self.conv1 = nn.Conv2d(1, 10, kernel_size=5)
        self.conv2 = nn.Conv2d(10, 20, kernel_size=5)
        self.conv2_drop = nn.Dropout2d()
        self.fc1 = nn.Linear(320, 50)
        self.fc2 = nn.Linear(50, 10)

    def forward(self, x):
        x = F.relu(F.max_pool2d(self.conv1(x), 2))
        x = F.relu(F.max_pool2d(self.conv2_drop(self.conv2(x)), 2))
        x = x.view(-1, 320)
        x = F.relu(self.fc1(x))
        x = F.dropout(x, training=self.training)
        x = self.fc2(x)
        return F.log_softmax(x)


# model = Net()
model = LissomCortexLayer((1, 784), (28, 28))
if args.cuda:
    model.cuda()

# optimizer = optim.SGD(model.parameters(), lr=args.lr, momentum=args.momentum)
optimizer = LissomHebbianOptimizer(0.1)


def train(epoch):
    model.train()
    for batch_idx, (data, target) in enumerate(train_loader):
        if args.cuda:
            data, target = data.cuda(), target.cuda()
        data, target = Variable(data), Variable(target)
        # optimizer.zero_grad()
        output = model(data, simple_lissom=True)
        # output - model(data)
        # loss = F.nll_loss(output, target)
        # loss.backward()

        optimizer.update_weights(model, simple_lissom=True)
        if batch_idx % args.log_interval == 0:
            print('Train Epoch: {} [{}/{} ({:.0f}%)]\tLoss: {:.6f}'.format(
                epoch, batch_idx * len(data), len(train_loader.dataset),
                       100. * batch_idx / len(train_loader), 100))

        if batch_idx < 2000 and (batch_idx < 5 or batch_idx % 100 == 0):
            images_numpy = [x.view(1, 1, 28, 28) for x in
                            [data.data, output, model.afferent_activation, model.inhibitory_activation,
                             model.excitatory_activation, model.retina_activation]]

            for title, im in zip(['input', 'output', 'model.afferent_activation', 'model.inhibitory_activation',
                                  'model.excitatory_activation', 'model.retina_activation'], images_numpy):
                vis.image(im, opts={'caption': title, 'height': 200, 'width': 200})
                im = vutils.make_grid(im)
                writer.add_image(title, im, batch_idx)

            weights = [w for w in map(summary_weights, [model.retina_weights, model.inhibitory_weights, model.excitatory_weights])]
            weights.append(summary_weights(model.retina_weights, last=True))
            images_numpy = [x.view(2, 1, 28, 28) for x in weights]
            for title, im in zip(['model.retina_weights_first', 'model.inhibitory_weights', 'model.excitatory_weights',
                                  'model.retina_weights_last'], images_numpy):
                im = vutils.make_grid(im, nrow=2)
                writer.add_image(title, im, batch_idx)

    writer.close()


def summary_weights(input, last=False, max_outputs=2):
    input = input * 28
    if last:
        input = input[:, -max_outputs:]
    else:
        input = input[:, :max_outputs]
    return torch.t(input).contiguous().data


def test():
    model.eval()
    test_loss = 0
    correct = 0
    for data, target in test_loader:
        if args.cuda:
            data, target = data.cuda(), target.cuda()
        data, target = Variable(data, volatile=True), Variable(target)
        output = model(data)
        test_loss += F.nll_loss(output, target, size_average=False).data[0]  # sum up batch loss
        pred = output.data.max(1, keepdim=True)[1]  # get the index of the max log-probability
        correct += pred.eq(target.data.view_as(pred)).cpu().sum()

    test_loss /= len(test_loader.dataset)
    print('\nTest set: Average loss: {:.4f}, Accuracy: {}/{} ({:.0f}%)\n'.format(
        test_loss, correct, len(test_loader.dataset),
        100. * correct / len(test_loader.dataset)))


for epoch in range(1, args.epochs + 1):
    train(epoch)
    # test()
