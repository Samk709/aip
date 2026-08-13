# FER-2013 CNN Model Evaluation & Benchmark Report

## Model Performance Summary

- **Architecture**: Lightweight MiniXception CNN (PyTorch)
- **Input Format**: 48x48 Grayscale Cropped Face Tensor `(1, 1, 48, 48)`
- **Classes (7)**: `angry`, `disgust`, `fear`, `happy`, `sad`, `surprise`, `neutral`
- **Training Data Source**: real FER-2013 CSV (data/train.csv)
- **Training Augmentation**: webcam simulation (rotation/translation, brightness/contrast jitter, gaussian blur, shadow gradients, CLAHE relighting, sensor noise)
- **Clean Test Accuracy**: `29.40%` | Macro F1: `0.2501`
- **Webcam-Shifted Test Accuracy**: `29.26%` | Macro F1: `0.2484`

## Classification Report (clean held-out test)

```text
              precision    recall  f1-score   support

       angry       0.29      0.11      0.16       491
     disgust       0.04      0.47      0.07        55
        fear       0.18      0.06      0.09       528
       happy       0.47      0.39      0.43       879
         sad       0.33      0.21      0.26       594
    surprise       0.35      0.76      0.48       416
     neutral       0.29      0.25      0.27       626

    accuracy                           0.29      3589
   macro avg       0.28      0.32      0.25      3589
weighted avg       0.33      0.29      0.29      3589

```

## Classification Report (webcam-shifted test)

```text
              precision    recall  f1-score   support

       angry       0.21      0.13      0.16       491
     disgust       0.05      0.27      0.08        55
        fear       0.17      0.10      0.13       528
       happy       0.43      0.42      0.43       879
         sad       0.26      0.27      0.27       594
    surprise       0.36      0.65      0.46       416
     neutral       0.27      0.19      0.22       626

    accuracy                           0.29      3589
   macro avg       0.25      0.29      0.25      3589
weighted avg       0.29      0.29      0.28      3589

```

## Confusion Matrix (clean held-out test)

| True \ Pred | angry | disgust | fear | happy | sad | surprise | neutral |
| --- | --- | --- | --- | --- | --- | --- | --- |
| **angry** | 55 | 93 | 20 | 66 | 64 | 122 | 71 |
| **disgust** | 4 | 26 | 0 | 14 | 3 | 5 | 3 |
| **fear** | 22 | 106 | 31 | 69 | 41 | 193 | 66 |
| **happy** | 29 | 181 | 38 | 347 | 72 | 94 | 118 |
| **sad** | 30 | 108 | 33 | 117 | 125 | 80 | 101 |
| **surprise** | 13 | 30 | 18 | 7 | 8 | 317 | 23 |
| **neutral** | 38 | 111 | 34 | 125 | 66 | 98 | 154 |
