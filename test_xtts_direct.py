"""
Test XTTS-Hindi using direct torch loading
"""
import sys
import os
os.chdir("C:/sourceCode/RadioExperiment")

# Try using xtts_v2 directly
from TTS.tts.configs.xtts_config import XttsConfig
from TTS.tts.models.xtts import Xtts
import torch

print("Loading XTTS-Hindi config...")
config = XttsConfig()
config.load_json("C:/sourceCode/TTS/xtts-hindi-model/config.json")

print("Loading XTTS model...")
model = Xtts.init_from_config(config)
model.load_checkpoint(
    config,
    checkpoint_dir="C:/sourceCode/TTS/xtts-hindi-model/",
    use_deepspeed=False
)

if torch.cuda.is_available():
    model.cuda()

print("\nGenerating Hindi speech...")
outputs = model.synthesize(
    "That was Kabhi Khushi Kabhie Gham from Rab Ne Bana Di Jodi",
    config,
    speaker_wav="voice_references/experiment_fm_intro_naksh.wav",
    language="hi"
)

print("✓ Generated!")
