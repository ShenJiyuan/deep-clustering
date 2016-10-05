# -*- coding: utf-8 -*-
"""
Created on Mon Sep 26 15:23:31 2016

@author: jcsilva
"""
import numpy as np
import random
import scipy.io.wavfile as wav
from python_speech_features import sigproc


FRAME_LENGTH = .032
FRAME_SHIFT = .008
FS = 8000
CONTEXT = 100
OVERLAP = 2


def squared_hann(M):
    return np.sqrt(np.hanning(M))


def stft(sig, rate):
    frames = sigproc.framesig(sig,
                              FRAME_LENGTH*rate,
                              FRAME_SHIFT*rate,
                              winfunc=squared_hann)
    spec = np.fft.rfft(frames, int(FRAME_LENGTH*rate))
    return np.log10(np.absolute(spec) + 1e-7)  # Log 10 for easier dB calculation


def get_egs(wavlist, min_mix=2, max_mix=3, sil_as_class=True):
    """
    Generate examples for the neural network from a list of wave files with
    speaker ids. Each line is of type "path speaker", as follows:

    path/to/1st.wav spk1
    path/to/2nd.wav spk2
    path/to/3rd.wav spk1

    and so on.
    min_mix and max_mix are the minimum and maximum number of examples to
    be mixed for generating a training example

    sil_as_class defines if the threshold-defined background silence will
    be treated as a separate class
    """
    speaker_wavs = {}
    while True:  # Generate examples indefinitely
        # Select number of files to mix
        k = np.random.randint(min_mix, max_mix+1)
        if k > len(speaker_wavs):
            # Reading wav files list and separating per speaker
            speaker_wavs = {}
            f = open(wavlist)
            for line in f:
                line = line.strip().split()
                if len(line) != 2:
                    continue
                p, spk = line
                if spk not in speaker_wavs:
                    speaker_wavs[spk] = []
                speaker_wavs[spk].append(p)
            f.close()
            # Randomizing wav lists
            for spk in speaker_wavs:
                random.shuffle(speaker_wavs[spk])
        wavsum = None
        sigs = []

        # Pop wav files from random speakers, store them individually for
        # dominant spectra decision and generate the mixed input
        for spk in random.sample(speaker_wavs.keys(), k):
            p = speaker_wavs[spk].pop()
            if not speaker_wavs[spk]:
                del(speaker_wavs[spk])  # Remove empty speakers from dictionary
            rate, sig = wav.read(p)
            sig = sig - np.mean(sig)
            sig = sig/np.max(np.abs(sig))
            sig *= (np.random.random()*1/4 + 3/4)
            if wavsum is None:
                wavsum = sig
            else:
                wavsum = wavsum[:len(sig)] + sig[:len(wavsum)]
            sigs.append(sig)

        # STFT for mixed signal
        X = np.real(stft(wavsum, rate))
        if len(X) <= CONTEXT:
            continue

        # STFTs for individual signals
        specs = []
        for sig in sigs:
            specs.append(stft(sig[:len(wavsum)], rate))
        specs = np.array(specs)

        if sil_as_class:
            nc = k + 1
        else:
            nc = k

        # Get dominant spectra indexes, create one-hot outputs
        Y = np.zeros(X.shape + (nc,))
        vals = np.argmax(specs, axis=0)
        for i in range(k):
            t = np.zeros(nc)
            t[i] = 1
            Y[vals == i] = t

        # EXPERIMENTAL: normalize mag spectra as weighted norm vectors instead
        # of using unit vectors for "hard" classes
#        if sil_as_class:
#            print("This won't work with sil_as_class=True")
#        from sklearn.preprocessing import normalize
#        Y = np.transpose(specs, (1, 2, 0))
#        Y = Y.reshape((-1, nc))
#        Y = normalize(Y, axis=1)
#        Y = Y.reshape(X.shape + (nc,))

        # Create mask for zeroing out gradients from silence components
        m = np.max(X) - 40./20  # Minus 40dB
        if sil_as_class:
            z = np.zeros(nc)
            z[-1] = 1
            Y[X < m] = z
        else:
            z = np.zeros(nc)
            Y[X < m] = z
        X -= np.mean(X)
        X /= np.std(X) + 1e-12
        i = 0

        # Generating sequences
        inp = []
        out = []
        while i + CONTEXT < len(X):
            inp.append(X[i:i+CONTEXT].reshape((-1,)))
            out.append(Y[i:i+CONTEXT].reshape((-1,)))
            i += CONTEXT // OVERLAP
        yield(np.expand_dims(np.array(inp), axis=0),
              np.expand_dims(np.array(out), axis=0))


if __name__ == "__main__":
    a = get_egs('wavlist_short', 2, 2, False)
    k = 6
    for i, j in a:
        print(i.shape, j.shape)
        k -= 1
        if k == 0:
            break
