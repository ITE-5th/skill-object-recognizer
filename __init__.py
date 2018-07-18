# File Path Manager
# import os
# sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
import socket
import sys
import traceback

from adapt.intent import IntentBuilder
from mycroft import MycroftSkill, intent_handler
from mycroft.util.log import LOG

from .code.message.object_recognition_message import ObjectRecognitionMessage
from .code.misc.camera import Camera
from .code.misc.receiver import Receiver
from .code.misc.sender import Sender
from .default_config import DefaultConfig

# TODO: Make sure "." before module name is not missing

LOG.warning('Running Skill Object Recognizer On Python ' + sys.version)

try:
    import picamera
    import inflect

except ImportError:
    # re-install yourself
    from msm import MycroftSkillsManager

    msm = MycroftSkillsManager()
    msm.install("https://github.com/ITE-5th/skill-object-recognizer")


class ObjectRecognizerSkill(MycroftSkill):
    def __init__(self):
        super(ObjectRecognizerSkill, self).__init__("ObjectRecognizerSkill")
        LOG.warning('Running Skill Object Recognizer ')
        self.socket = None
        self.receiver = None
        self.sender = None
        self.port = None
        self.host = None
        self.camera = Camera(width=800, height=600)
        self.p = inflect.engine()
        self.connect()

    def connect(self):
        try:
            self.port = DefaultConfig.OBJECT_RECOGNITION_PORT
            self.host = self.settings.get("server_url", DefaultConfig.server_url)
            LOG.info("Object Recognizer Skill started " + self.host + ":" + str(self.port))
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(10)
            self.socket.connect((self.host, self.port))
            self.receiver = Receiver(self.socket, json=True)
            self.sender = Sender(self.socket, json=True)
            LOG.info('connected to server:' + self.host + ' : ' + str(self.port))
        except Exception as e:
            LOG.warning(str(e))

    def ensure_send(self, msg):
        retries = 3
        while retries > 0:
            try:
                retries -= 1
                self.sender.send(msg)
                break
            except Exception as e:
                if retries <= 0:
                    raise ConnectionError()
                self.connect()
                LOG.warning(str(e))
        return True

    @intent_handler(IntentBuilder("ORIntent").require('Count').optionally('Object').optionally('Everything'))
    def answer(self, message):
        try:

            print(message.data)
            object_name = None
            everything = True if message.data.get("Everything", None) else False
            if not everything:
                # Search for the object
                object_name = message.data.get("Object", None)
                if object_name is not None:
                    utterance = message.data.get('utterance', '')
                    object_name = ''.join(utterance.split('count'))
                else:
                    self.speak_dialog('GetObject')
                    object_name = self.get_phrase()

            image, _ = self.camera.take_image()
            msg = ObjectRecognitionMessage(image=image)
            self.ensure_send(msg)
            response = self.receiver.receive()
            LOG.info(response)

            result = self.handle_message(response.get('result'), object_name)
            # Speak Result
            if result:
                if everything:
                    self.speak_dialog("ResultAll", result)
                else:
                    self.speak_dialog("ResultSingle", result)
            else:
                self.speak_dialog("NoResult", result)

        except LookupError as e:
            self.speak_dialog('GetObjectError')

        except ConnectionError as e:
            self.speak_dialog('ConnectionError')

        except Exception as e:
            LOG.info('Something is wrong')
            LOG.info(str(e))
            LOG.info(str(traceback.format_exc()))
            self.speak_dialog("UnknownError")
            self.connect()
        return True

    def handle_message(self, response, desired_object=None):
        """
        converts server response to meaningful sentence
        :param desired_object: string represents object name to search
        :param response: string of answers
        :return: dictionary contains sentence in result
        """

        if not response:
            return None

        if desired_object:
            desired_object = self.p.singular_noun(desired_object).strip().lower()
            return {
                'object': desired_object,
                'count': response[desired_object]
            }

        else:

            result = ["{} {}".format(value, self.p.plural(key, value.capitalize())) for key, value in response.items()]
            return {'result': ",".join(result)}

    @staticmethod
    def get_phrase(lang='en-US'):
        import speech_recognition as sr
        r = sr.Recognizer()

        with sr.Microphone() as source:
            print('recording...')
            audio = r.listen(source)
        print('fin recording...')

        try:
            text = r.recognize_google(audio, language=lang)
            print("Google Speech Recognition thinks you said " + text)

            if text is not None or text.strip() != "":
                return text
            raise LookupError()

        except sr.UnknownValueError:
            print("Google Speech Recognition could not understand audio")
            raise LookupError()
        except sr.RequestError as e:
            print("Could not request results from Google Speech Recognition service; {0}".format(e))
            raise LookupError()

    def stop(self):
        super(ObjectRecognizerSkill, self).shutdown()
        LOG.info("Object Recognizer Skill CLOSED")
        self.socket.close()


def create_skill():
    return ObjectRecognizerSkill()
