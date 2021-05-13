import kivy
from kivy.app import App
from kivy.uix.label import Label


class MyFirstKivyApp(App):
    def build(self):
        return Label(text="Welcome To Kivy World !!!")


if __name__ == "__main__":
    MyFirstKivyApp().run()