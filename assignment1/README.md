# Speech Synthesis 🦜
You are asked to synthesize some vowels (monophthongs) using the source-filter model of speech production. The process involves:
- Estimating the formant structure of each vowel directly from a real speech sample, using linear predictive coding (LPC)
- Generating synthesized vowels by passing a periodic impulse train through the all-pole filter obtained

## Directory Layout
The helper functions can be found in the `assignment_1` directory. All the files ending in `.m` are MATLAB functions and the actual speech synthesis and analysis is done in the `speech_synthesis.mlx` file.

The `speech` directory contains the audio files used in the assignment. The `synthesized_impulse` and `synthesized_sawtooth` directories contain the synthesized audio files.

```bash
assignment_1
├── LICENSE
├── README.md
└── assignment_1
    ├── assignment1_submission.pdf
    ├── assignment1_spec.pdf
    ├── estimateF0ByAutoCorrelation.m
    ├── estimateF0ByPowerSpectrum.m
    ├── estimateFormants.m
    ├── extractCenterSegment.m
    ├── orderAnalysis.m
    ├── orderSegmentAnalysis.m
    ├── playAudio.m
    ├── plotLPCPoleZero.m
    ├── plotLPCResponse.m
    ├── plotSpectrogram.m
    ├── plotSynthesis.m
    ├── segmentAnalysis.m
    ├── speech
    ├── speech_synthesis.mlx
    ├── synthesizeLPC.m
    ├── synthesized_impulse
    └── synthesized_sawtooth
```