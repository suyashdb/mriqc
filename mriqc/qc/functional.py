#!/usr/bin/env python
# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
# pylint: disable=no-member
#
# @Author: oesteban
# @Date:   2016-02-23 19:25:39
# @Email:  code@oscaresteban.es
# @Last Modified by:   oesteban
# @Last Modified time: 2016-09-15 10:24:45
"""
Computation of the quality assessment measures on functional MRI



"""
from __future__ import print_function, division, absolute_import, unicode_literals
import os.path as op
import numpy as np
import nibabel as nb
from nipype.algorithms.confounds import zero_variance


def gsr(epi_data, mask, direction="y", ref_file=None, out_file=None):
    """
    Computes the :abbr:`GSR (ghost to signal ratio)` [Giannelli2010]_. The
    procedure is as follows:

      #. Create a Nyquist ghost mask by circle-shifting the original mask by :math:`N/2`.

      #. Rotate by :math:`N/2`

      #. Remove the intersection with the original mask

      #. Generate a non-ghost background

      #. Calculate the :abbr:`GSR (ghost to signal ratio)`


    .. warning ::

      This should be used with EPI images for which the phase
      encoding direction is known.

    :param str epi_file: path to epi file
    :param str mask_file: path to brain mask
    :param str direction: the direction of phase encoding (x, y, all)
    :return: the computed gsr

    """

    direction = direction.lower()
    if direction[-1] not in ['x', 'y', 'all']:
        raise Exception("Unknown direction {}, should be one of x, -x, y, -y, all".format(
            direction))

    if direction == 'all':
        result = []
        for newdir in ['x', 'y']:
            ofile = None
            if out_file is not None:
                fname, ext = op.splitext(ofile)
                if ext == '.gz':
                    fname, ext2 = op.splitext(fname)
                    ext = ext2 + ext
                ofile = '{0}_{1}{2}'.format(fname, newdir, ext)
            result += [gsr(epi_data, mask, newdir,
                           ref_file=ref_file, out_file=ofile)]
        return result

    # Step 1
    n2_mask = np.zeros_like(mask)

    # Step 2
    if direction == "x":
        n2max = mask.shape[0]
        n2lim = int(np.floor(n2max/2))
        n2_mask[:n2lim, :, :] = mask[n2lim:n2max, :, :]
        n2_mask[n2lim:n2max, :, :] = mask[:n2lim, :, :]
    elif direction == "y":
        n2max = mask.shape[1]
        n2lim = int(np.floor(n2max/2))
        n2_mask[:, :n2lim, :] = mask[:, n2lim:n2max, :]
        n2_mask[:, n2lim:n2max, :] = mask[:, :n2lim, :]
    elif direction == "z":
        n2max = mask.shape[2]
        n2lim = int(np.floor(n2max/2))
        n2_mask[:, :, :n2lim] = mask[:, :, n2lim:n2max]
        n2_mask[:, :, n2lim:n2max] = mask[:, :, :n2lim]

    # Step 3
    n2_mask = n2_mask * (1-mask)

    # Step 4: non-ghost background region is labeled as 2
    n2_mask = n2_mask + 2 * (1 - n2_mask - mask)

    # Save mask
    if ref_file is not None and out_file is not None:
        ref = nb.load(ref_file)
        out = nb.Nifti1Image(n2_mask, ref.get_affine(), ref.get_header())
        out.to_filename(out_file)

    # Step 5: signal is the entire foreground image
    ghost = epi_data[n2_mask == 1].mean() - epi_data[n2_mask == 2].mean()
    signal = epi_data[n2_mask == 0].mean()
    return float(ghost/signal)


def gcor(func, mask):
    """
    Compute the :abbr:`GCOR (global correlation)`.

    :param numpy.ndarray func: input fMRI dataset, after motion correction
    :param numpy.ndarray mask: 3D brain mask
    :return: the computed GCOR value

    """
    from scipy.stats.mstats import zscore
    # Remove zero-variance voxels across time axis
    tv_mask = zero_variance(func, mask)
    idx = np.where(tv_mask > 0)
    zscores = zscore(func[idx[0], idx[1], idx[2], :], axis=1)
    avg_ts = zscores.mean(axis=0)
    return float(avg_ts.transpose().dot(avg_ts) / len(avg_ts))
