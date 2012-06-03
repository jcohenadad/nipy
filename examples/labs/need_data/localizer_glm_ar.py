# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
"""
Full step-by-step example of fitting a GLM to experimental data and
visualizing the results.

More specifically,
1. A sequence of fMRI volumes are loaded
2. A design matrix describing all the effects related to the data is computed
3. a mask of the useful brain volume is computed
4. A GLM is applied to the dataset (effect/covariance,
   then contrast estimation)

Note that this corresponds to a single run.

Author : Bertrand Thirion, 2010
"""
print __doc__

import numpy as np
import os.path as op
import pylab as pl
import tempfile

from nibabel import load, save, Nifti1Image
from nipy.modalities.fmri.glm import glm_fit
from nipy.modalities.fmri.design_matrix import make_dmtx
from nipy.modalities.fmri.experimental_paradigm import \
    load_paradigm_from_csv_file
from nipy.labs.viz import plot_map, cm
from nipy.labs import compute_mask_files

import get_data_light

#######################################
# Data and analysis parameters
#######################################

# volume mask
get_data_light.get_first_level_dataset()
data_path = op.expanduser(op.join('~', '.nipy', 'tests', 'data',
                                 's12069_swaloc1_corr.nii.gz'))
paradigm_file = op.expanduser(op.join('~', '.nipy', 'tests', 'data',
                                      'localizer_paradigm.csv'))

# timing
n_scans = 128
tr = 2.4

# paradigm
frametimes = np.linspace(0, (n_scans - 1) * tr, n_scans)
conditions = ['damier_H', 'damier_V', 'clicDaudio', 'clicGaudio', 'clicDvideo',
              'clicGvideo', 'calculaudio', 'calculvideo', 'phrasevideo',
              'phraseaudio']

# confounds
hrf_model = 'canonical with derivative'
drift_model = "cosine"
hfcut = 128

# write directory
write_dir = tempfile.mkdtemp()
print 'Computation will be performed in temporary directory: %s' % write_dir

########################################
# Design matrix
########################################

print 'Loading design matrix...'

paradigm = load_paradigm_from_csv_file(paradigm_file).values()[0]

design_matrix = make_dmtx(frametimes, paradigm, hrf_model=hrf_model,
                          drift_model=drift_model, hfcut=hfcut)

ax = design_matrix.show()
ax.set_position([.05, .25, .9, .65])
ax.set_title('Design matrix')

pl.savefig(op.join(write_dir, 'design_matrix.png'))
# design_matrix.write_csv(...)

########################################
# Mask the data
########################################

print 'Computing a brain mask...'
mask_path = op.join(write_dir, 'mask.nii')
mask_array = compute_mask_files(data_path, mask_path, False, 0.4, 0.9)

#########################################
# Specify the contrasts
#########################################

# simplest ones
contrasts = {}
contrast_id = conditions
for i in range(len(conditions)):
    contrasts['%s' % conditions[i]] = np.eye(len(design_matrix.names))[2 * i]

# and more complex/ interesting ones
contrasts["audio"] = contrasts["clicDaudio"] + contrasts["clicGaudio"] +\
                     contrasts["calculaudio"] + contrasts["phraseaudio"]
contrasts["video"] = contrasts["clicDvideo"] + contrasts["clicGvideo"] + \
                     contrasts["calculvideo"] + contrasts["phrasevideo"]
contrasts["left"] = contrasts["clicGaudio"] + contrasts["clicGvideo"]
contrasts["right"] = contrasts["clicDaudio"] + contrasts["clicDvideo"]
contrasts["computation"] = contrasts["calculaudio"] + contrasts["calculvideo"]
contrasts["sentences"] = contrasts["phraseaudio"] + contrasts["phrasevideo"]
contrasts["H-V"] = contrasts["damier_H"] - contrasts["damier_V"]
contrasts["V-H"] = contrasts["damier_V"] - contrasts["damier_H"]
contrasts["left-right"] = contrasts["left"] - contrasts["right"]
contrasts["right-left"] = contrasts["right"] - contrasts["left"]
contrasts["audio-video"] = contrasts["audio"] - contrasts["video"]
contrasts["video-audio"] = contrasts["video"] - contrasts["audio"]
contrasts["computation-sentences"] = contrasts["computation"] -  \
                                     contrasts["sentences"]
contrasts["reading-visual"] = contrasts["sentences"] * 2 - \
                              contrasts["damier_H"] - contrasts["damier_V"]
contrasts['effects_of_interest'] = np.eye(25)[::2]

########################################
# Perform a GLM analysis
########################################

print 'Fitting a GLM (this takes time)...'
fmri_image = load(data_path)
Y = fmri_image.get_data()[mask_array]
X = design_matrix.matrix
results = glm_fit(X, Y.T, steps=2)
affine = fmri_image.get_affine()

#########################################
# Estimate the contrasts
#########################################

print 'Computing contrasts...'
for index, (contrast_id, contrast_val) in enumerate(contrasts.iteritems()):
    print '  Contrast % 2i out of %i: %s' % (
        index + 1, len(contrasts), contrast_id)
    contrast_path = op.join(write_dir, '%s_z_map.nii' % contrast_id)
    write_array = mask_array.astype(np.float)
    write_array[mask_array] = results.contrast(contrast_val).z_score()
    contrast_image = Nifti1Image(write_array, affine)
    save(contrast_image, contrast_path)

    vmax = max(- write_array.min(), write_array.max())
    plot_map(write_array, affine,
             cmap=cm.cold_hot,
             vmin=- vmax,
             vmax=vmax,
             anat=None,
             figure=10,
             threshold=2.5)
    pl.savefig(op.join(write_dir, '%s_z_map.png' % contrast_id))
    pl.clf()


#########################################
# End
#########################################

print "All the  results were witten in %s" % write_dir

plot_map(write_array, affine,
         cmap=cm.cold_hot,
         vmin=- vmax,
         vmax=vmax,
         anat=None,
         figure=10,
         threshold=3)

"""
plot_map(write_array, affine,
                cmap=cm.cold_hot,
                vmin=-vmax,
                vmax=vmax,
                anat=None,
                figure=10,
                threshold=3, do3d=True)

from nipy.labs import viz3d
viz3d.plot_map_3d(write_array, affine,
                cmap=cm.cold_hot,
                vmin=-vmax,
                vmax=vmax,
                anat=None,
                threshold=3)
"""
pl.show()
