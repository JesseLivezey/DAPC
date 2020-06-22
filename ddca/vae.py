import math
import torch
import torch.nn as nn
from torch.nn import functional as F
from torch import optim

from .math import log_density_gaussian, log_importance_weight_matrix, matrix_log_density_gaussian


def btcvae_loss(latent_dist, latent_sample, n_data, is_mss=True, alpha=1., beta=6.):
    batch_size, latent_dim = latent_sample.shape

    #print("latent_dist:", latent_dist[0].shape, latent_dist[1].shape)
    #print("latent_sample:", latent_sample.shape)
    log_pz, log_qz, log_prod_qzi, log_q_zCx = _get_log_pz_qz_prodzi_qzCx(latent_sample,
                                                                         latent_dist,
                                                                         n_data,
                                                                         is_mss=is_mss)
    # I[z;x] = KL[q(z,x)||q(x)q(z)] = E_x[KL[q(z|x)||q(z)]]
    mi_loss = (log_q_zCx - log_qz).mean()
    # TC[z] = KL[q(z)||\prod_i z_i]
    tc_loss = (log_qz - log_prod_qzi).mean()
    # dw_kl_loss is KL[q(z)||p(z)] instead of usual KL[q(z|x)||p(z))]
    # dw_kl_loss = (log_prod_qzi - log_pz).mean()
    # anneal_reg = (linear_annealing(0, 1, self.n_train_steps, self.steps_anneal) if is_train else 1)

    # total loss
    loss = alpha * mi_loss + beta * tc_loss
    return loss


def _get_log_pz_qz_prodzi_qzCx(latent_sample, latent_dist, n_data, is_mss=True):
    batch_size, hidden_dim = latent_sample.shape

    # calculate log q(z|x)
    log_q_zCx = log_density_gaussian(latent_sample, *latent_dist).sum(dim=1)

    # calculate log p(z)
    # mean and log var is 0
    zeros = torch.zeros_like(latent_sample)
    log_pz = log_density_gaussian(latent_sample, zeros, zeros).sum(1)

    mat_log_qz = matrix_log_density_gaussian(latent_sample, *latent_dist)

    if is_mss:
        # use stratification
        log_iw_mat = log_importance_weight_matrix(batch_size, n_data).to(latent_sample.device)
        mat_log_qz = mat_log_qz + log_iw_mat.view(batch_size, batch_size, 1)

    log_qz = torch.logsumexp(mat_log_qz.sum(2), dim=1, keepdim=False)
    log_prod_qzi = torch.logsumexp(mat_log_qz, dim=1, keepdim=False).sum(1)

    return log_pz, log_qz, log_prod_qzi, log_q_zCx


