"""US identity data generator: name, address, phone (Washington DC)."""

import random

FIRST_MALE = [
    "James", "John", "Robert", "Michael", "David", "William", "Richard",
    "Joseph", "Thomas", "Charles", "Christopher", "Daniel", "Matthew",
    "Anthony", "Mark", "Steven", "Andrew", "Joshua", "Kenneth", "Kevin",
    "Brian", "George", "Timothy", "Ronald", "Jason", "Edward", "Jeffrey",
    "Ryan", "Jacob", "Gary", "Nicholas", "Eric", "Jonathan", "Stephen",
    "Larry", "Justin", "Scott", "Brandon", "Benjamin", "Samuel", "Patrick",
    "Raymond", "Gregory", "Frank", "Alexander", "Dennis", "Jerry", "Tyler",
    "Aaron", "Nathan",
]

FIRST_FEMALE = [
    "Mary", "Patricia", "Jennifer", "Linda", "Barbara", "Elizabeth",
    "Susan", "Jessica", "Sarah", "Karen", "Lisa", "Nancy", "Betty",
    "Margaret", "Sandra", "Ashley", "Dorothy", "Kimberly", "Emily",
    "Donna", "Michelle", "Carol", "Amanda", "Melissa", "Deborah",
    "Stephanie", "Rebecca", "Sharon", "Laura", "Cynthia", "Kathleen",
    "Amy", "Angela", "Shirley", "Anna", "Brenda", "Pamela", "Nicole",
    "Samantha", "Katherine", "Christine", "Helen", "Debra", "Rachel",
    "Carolyn", "Janet", "Catherine", "Maria", "Heather", "Diane",
]

LAST_NAME = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
    "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez",
    "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin",
    "Lee", "Perez", "Thompson", "White", "Harris", "Sanchez", "Clark",
    "Ramirez", "Lewis", "Robinson", "Walker", "Young", "Allen", "King",
    "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores", "Green",
    "Adams", "Nelson", "Baker", "Hall", "Rivera", "Campbell", "Mitchell",
    "Carter", "Roberts",
]

STREETS = [
    "Pennsylvania Ave NW", "Connecticut Ave NW", "Wisconsin Ave NW",
    "Massachusetts Ave NW", "Georgia Ave NW", "Rhode Island Ave NE",
    "Bladensburg Rd NE", "Benning Rd NE", "Martin Luther King Jr Ave SE",
    "South Capitol St SW", "North Capitol St NE", "New Jersey Ave SE",
    "New York Ave NE", "Florida Ave NW", "Michigan Ave NE",
    "Nebraska Ave NW", "Alabama Ave SE", "Minnesota Ave NE",
    "East Capitol St NE", "H St NE", "K St NW", "M St NW",
    "U St NW", "14th St NW", "16th St NW", "7th St NW",
    "Constitution Ave NW", "Independence Ave SW", "Columbia Rd NW",
    "Irving St NW", "Park Rd NW", "Sherman Ave NW", "Calvert St NW",
    "Euclid St NW", "Harvard St NW", "Kenyon St NW", "Lamont St NW",
    "Monroe St NE", "Otis St NE", "Quincy St NE", "Randolph St NW",
    "Taylor St NE", "Upshur St NW", "Varnum St NW", "Webster St NW",
    # DC taxi registry addresses
    "5th St NE", "Benning Rd NE", "Bladensburg Rd NE", "Q St SW",
    "Earl Place NE", "West Virginia Ave NE", "Kenilworth Ave NE",
    "Lawrence Ave NE", "Adams St NE", "Franklin St NE",
    "Rhode Island Ave NE", "Evarts St NE", "26th St NE",
    "New York Ave NW", "L St SE", "22nd St NE", "6th St NW",
    "New Jersey Ave SE", "Sligo Mill Rd NE", "Georgia Ave NW",
    "Rhode Island Ave NE", "Upshur St NW", "M L King Jr Ave SE",
]

CITIES = [
    {"city": "Washington", "state": "DC", "zips": ("20001", "20020")},
]

DC_TAXI_PHONES = [
    "2028324662", "2028324441", "2026367280", "2023980526", "2022691100",
    "2026353498", "2026360087", "2026355001", "2027253962", "2024847100",
    "2025267215", "2022696690", "2025290330", "2022918300", "2025541200",
    "2024841200", "2022699000", "2025265655", "2023324444", "2023875302",
    "2025467900", "2026356498", "2023987980", "2024880526", "2024885555",
    "2022699831", "2024841200", "2022691200", "2025291220", "2025547900",
    "2022699000", "2025267215", "2026366690", "2024885555", "2022697280",
    "2024844844", "2022700700", "2025541200", "2026350526", "2026360087",
    "2026355001", "2027253962", "2024847100", "2022691100", "2022691100",
    "2023324662", "2022697007", "2023980526", "2024841200", "2022699000",
    "2022162370", "2028320436", "2025267215", "2026367280", "2025414015",
    "2022912300", "2022322300", "2022884662", "2022697215", "2023980526",
]

_DC_ZIPS = [
    "20001", "20002", "20003", "20005", "20006", "20007", "20008", "20009",
    "20010", "20011", "20012", "20015", "20016", "20017", "20018", "20019",
    "20020", "20024", "20032", "20036", "20037",
]


def random_name() -> str:
    """Generate a random American full name."""
    first = random.choice(FIRST_MALE if random.random() < 0.5 else FIRST_FEMALE)
    last = random.choice(LAST_NAME)
    return f"{first} {last}"


def random_address() -> dict:
    """Generate a random Washington DC address."""
    street = random.choice(STREETS)
    number = random.randint(100, 4999)
    apt = ""
    if random.random() < 0.3:
        apt = f" Apt {random.randint(1, 12)}{random.choice(['', 'A', 'B', 'C'])}"

    return {
        "street": f"{number} {street}{apt}",
        "city": "Washington",
        "state": "DC",
        "postal": random.choice(_DC_ZIPS),
    }


def random_phone() -> str:
    """Return a DC taxi company phone number (10 digits, no prefix)."""
    return random.choice(DC_TAXI_PHONES)
