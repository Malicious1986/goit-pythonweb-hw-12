import cloudinary
import cloudinary.uploader


class UploadFileService:
    """Upload files to Cloudinary and return a resized image URL.

    The class configures the global Cloudinary client on initialization and
    exposes a static helper to upload a file and return a small avatar URL.
    """

    def __init__(self, cloud_name, api_key, api_secret):
        """Configure Cloudinary credentials.

        Args:
            cloud_name (str): Cloudinary cloud name.
            api_key (str): API key.
            api_secret (str): API secret.
        """

        self.cloud_name = cloud_name
        self.api_key = api_key
        self.api_secret = api_secret
        cloudinary.config(
            cloud_name=self.cloud_name,
            api_key=self.api_key,
            api_secret=self.api_secret,
            secure=True,
        )

    @staticmethod
    def upload_file(file, username) -> str:
        """Upload the given file and return a Cloudinary image URL.

        Args:
            file: File-like object with a ``file`` attribute (e.g., FastAPI UploadFile).
            username (str): Username used to build the public id.

        Returns:
            str: URL of the uploaded and resized image.
        """

        public_id = f"RestApp/{username}"
        r = cloudinary.uploader.upload(file.file, public_id=public_id, overwrite=True)
        src_url = cloudinary.CloudinaryImage(public_id).build_url(
            width=250, height=250, crop="fill", version=r.get("version")
        )
        return src_url
