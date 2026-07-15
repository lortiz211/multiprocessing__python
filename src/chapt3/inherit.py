from typing import ClassVar, Any, Protocol
from pprint import pprint


# Adding Protocol classes
class Emailable(Protocol):
    email: str


class MailSender(Emailable):
    def send_email(self, message: str) -> None:
        print(f"Sending email to {self.email}")


# extending built ins
class ContactList(list["Contact"]):
    def search(self, name: str) -> list[Contact]:
        matching_contacts: list[Contact] = []
        for contact in self:
            if name in contact.name:
                matching_contacts.append(contact)
        return matching_contacts


class Contact:
    all_contacts: ClassVar[ContactList] = ContactList()

    def __init__(self, name: str, email: str):
        self.name = name
        self.email = email
        Contact.all_contacts.append(self)

    def __repr__(self):
        return f"{self.__class__.__name__}({self.name}, {self.email})"


class Supplier(Contact):
    def order(self, order: Any) -> None:
        print(
            f"if this were a real system we would send '{order}' order to '{self.name}'"
        )


# Multiple inheritance
class EmailableContact(Contact, MailSender):
    pass


def main():
    c1 = Contact("Some Body", "some.body@email.com")
    s1 = Supplier("Su Plier", "suplier@email.com")
    e1 = EmailableContact("Email Lable", "emailable@email.com")

    pprint(c1.all_contacts)
    pprint(c1.all_contacts.search("John"))
