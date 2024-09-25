# SmartLocker
In this project, I developed a Smart Locker System that provides users access to their locker through facial biometric authentication. The project utilized Python, specifically the dlib library, for face recognition, along with an anti-spoofing mechanism that detects eye blinking to prevent fraudulent access attempts.

Key Features:

Facial Biometric Authentication: We implemented face detection using the dlib library, ensuring accurate recognition of users.

Anti-Spoofing: To enhance security, we integrated an eye-blinking detection feature to prevent unauthorized access through static images.

Document Verification: We incorporated PAN card OCR for document verification, making it an all-encompassing solution for identity verification.

Backend Architecture: The backend was designed using Flask, which served as the web framework for the server-side logic. For database management, we used MongoDB to store user data and access logs efficiently.
