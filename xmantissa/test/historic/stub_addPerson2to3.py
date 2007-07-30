from axiom.test.historic.stubloader import saveStub
from xmantissa.people import AddPerson
from axiom.dependency import installOn

def createDatabase(s):
    installOn(AddPerson(store=s), s)

if __name__ == '__main__':
    saveStub(createDatabase, 13144)
