from .image_message import ImageMessage


class ObjectRecognitionMessage(ImageMessage):
    def __init__(self, image, object_name):
        super().__init__(image=image)
        self.object_name = object_name
