from rembg import remove
from PIL import Image

input_path = "removeBackgroundofit.jpeg"
output_path = "removedBackground.png"

input_image = Image.open(input_path)
# output_image = remove(input_image)
# output_image.save(output_path)


import cv2
import numpy as np
from PIL import Image


import cv2
import numpy as np
from PIL import Image

# Load image
# input_path = "Screenshot_2025-10-24_at_9.52.45_PM.png"
# output_path = "no_sky.png"

# Read and convert to HSV
img = cv2.imread(input_path)
hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

# --- Define the color range for sky ---
# Adjust these if needed depending on your lighting
lower_sky = np.array([90, 0, 120])   # H, S, V lower bound
upper_sky = np.array([140, 80, 255]) # H, S, V upper bound

# Create a mask for the sky
mask = cv2.inRange(hsv, lower_sky, upper_sky)

# Invert mask so we keep everything except the sky
mask_inv = cv2.bitwise_not(mask)

# Apply mask to image
result = cv2.bitwise_and(img, img, mask=mask_inv)

# Convert to RGBA (make sky transparent)
rgba = cv2.cvtColor(result, cv2.COLOR_BGR2BGRA)
rgba[:, :, 3] = mask_inv

# Save result
cv2.imwrite(output_path, rgba)
print(f"✅ Sky removed and saved to {output_path}")



# Load the image
# img = cv2.imread(input_path)
# hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

# # Define the HSV range for sky (tweak these)
# lower_sky = np.array([223	,176	,158				])

# upper_sky = np.array([207	,218	,223					])



# # Create mask
# mask = cv2.inRange(hsv, upper_sky,lower_sky )

# # Invert mask to keep everything *except* the sky
# mask_inv = cv2.bitwise_not(mask)

# # Apply mask
# result = cv2.bitwise_and(img, img, mask=mask_inv)

# # Convert to RGBA and make sky transparent
# rgba = cv2.cvtColor(result, cv2.COLOR_BGR2BGRA)
# rgba[:, :, 3] = mask_inv  # transparency from mask

# cv2.imwrite("removed_v2.png", rgba)


# # import cv2
# # import numpy as np
# # from PIL import Image

# # # Load the image
# # img = cv2.imread(input_image)
# # hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

# # # Define the HSV range for sky (tweak these)
# # lower_sky = np.array([90, 10, 120])
# # upper_sky = np.array([130, 255, 255])

# # # Create mask
# # mask = cv2.inRange(hsv, lower_sky, upper_sky)

# # # Invert mask to keep everything *except* the sky
# # mask_inv = cv2.bitwise_not(mask)

# # # Apply mask
# # result = cv2.bitwise_and(img, img, mask=mask_inv)

# # # Convert to RGBA and make sky transparent
# # rgba = cv2.cvtColor(result, cv2.COLOR_BGR2BGRA)
# # rgba[:, :, 3] = mask_inv  # transparency from mask

# # cv2.imwrite("removed_v3.png", rgba)

# # # from rembg import remove, new_session
# # # from PIL import Image, ImageFilter
# # # import io
# # # session = new_session(model_name="isnet-general-use")
# # # with open(input_path, "rb") as i:
# # #     input_data = i.read()
# # #     # result = remove(i.read(), model_name="isnet-general-use")
# # # result = remove(input_data, session=session)
# # # with open("removeBackground_second.png", "wb") as o:
# # #     o.write(result)

# # # # # Open result as image
# # # # img = Image.open(io.BytesIO(result)).convert("RGBA")

# # # # # Slightly blur alpha mask (to soften or restore edges)
# # # # alpha = img.split()[-1].filter(ImageFilter.GaussianBlur(radius=2))
# # # # img.putalpha(alpha)

# # # # img.save("removeBackground_second.png")
