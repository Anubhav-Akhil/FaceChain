# Sample Images

Place test images in this directory to run the pipeline.

## Example usage:
```bash
python run_pipeline.py --image sample_images/test_face.jpg
```

## Tips for best results:
- Use a clear, well-lit photo with a visible face
- Front-facing portraits work best with the HOG model
- For side profiles or difficult angles, use `--model cnn`
- Celebrity or public figure photos tend to have more search results
