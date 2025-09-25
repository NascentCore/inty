/**
 * 随机英文名字生成器
 * 用于为智能体角色生成随机的英文名字
 */

// 男性英文名字列表
const MALE_NAMES = [
  "Alexander",
  "Benjamin",
  "Christopher",
  "Daniel",
  "Ethan",
  "Felix",
  "Gabriel",
  "Henry",
  "Isaac",
  "James",
  "Kevin",
  "Liam",
  "Michael",
  "Nathan",
  "Oliver",
  "Patrick",
  "Quinn",
  "Ryan",
  "Samuel",
  "Thomas",
  "Victor",
  "William",
  "Xavier",
  "Zachary",
  "Aaron",
  "Blake",
  "Caleb",
  "David",
  "Eli",
  "Finn",
  "George",
  "Hunter",
  "Ian",
  "Jake",
  "Kyle",
  "Luke",
  "Marcus",
  "Noah",
  "Owen",
  "Paul",
  "Robert",
  "Sean",
  "Tyler",
  "Vincent",
  "Wesley",
  "Adam",
  "Brandon",
  "Charles",
  "Derek",
  "Eric",
  "Frank",
  "Grant",
  "Hugo",
  "Ivan",
  "Jack",
  "Leo",
  "Max",
  "Nick",
  "Oscar",
  "Peter",
  "Quentin",
  "Richard",
  "Steven",
];

const LAST_NAMES = [
  "Smith",
  "Johnson",
  "Williams",
  "Brown",
  "Jones",
  "Garcia",
  "Miller",
  "Davis",
  "Rodriguez",
  "Martinez",
  "Hernandez",
  "Lopez",
  "Gonzalez",
  "Wilson",
  "Anderson",
  "Thomas",
  "Taylor",
  "Moore",
  "Jackson",
  "Martin",
  "Lee",
  "Perez",
  "Thompson",
  "White",
  "Harris",
  "Sanchez",
  "Clark",
  "Ramirez",
  "Lewis",
  "Robinson",
  "Walker",
  "Young",
  "Allen",
  "King",
  "Wright",
  "Scott",
  "Torres",
  "Nguyen",
  "Hill",
  "Flores",
  "Green",
  "Adams",
  "Nelson",
  "Baker",
  "Hall",
  "Rivera",
  "Campbell",
  "Mitchell",
  "Carter",
  "Roberts",
];

// 女性英文名字列表
const FEMALE_NAMES = [
  "Amelia",
  "Bella",
  "Charlotte",
  "Diana",
  "Emma",
  "Fiona",
  "Grace",
  "Hannah",
  "Isabella",
  "Julia",
  "Kate",
  "Lily",
  "Mia",
  "Nora",
  "Olivia",
  "Penelope",
  "Quinn",
  "Ruby",
  "Sophia",
  "Tessa",
  "Victoria",
  "Willa",
  "Zoe",
  "Abigail",
  "Brianna",
  "Chloe",
  "Delilah",
  "Elena",
  "Faith",
  "Gabrielle",
  "Hazel",
  "Iris",
  "Jasmine",
  "Katherine",
  "Luna",
  "Maya",
  "Natalie",
  "Ophelia",
  "Paisley",
  "Riley",
  "Stella",
  "Talia",
  "Uma",
  "Violet",
  "Willow",
  "Xara",
  "Yara",
  "Zara",
  "Alice",
  "Brooke",
  "Cora",
  "Daisy",
  "Eva",
  "Freya",
  "Gia",
  "Harper",
  "Ivy",
  "Jade",
  "Kira",
  "Layla",
  "Mila",
  "Nina",
  "Orla",
  "Piper",
  "Rose",
  "Sage",
];

// 中性英文名字列表
const NEUTRAL_NAMES = [
  "Alex",
  "Avery",
  "Blake",
  "Cameron",
  "Dakota",
  "Emery",
  "Finley",
  "Gray",
  "Harper",
  "Indigo",
  "Jordan",
  "Kai",
  "Lane",
  "Morgan",
  "Nico",
  "Ocean",
  "Parker",
  "Quinn",
  "River",
  "Sage",
  "Taylor",
  "Val",
  "Winter",
  "Xen",
  "Yael",
  "Zion",
  "Adrian",
  "Bailey",
  "Casey",
  "Drew",
  "Ellis",
  "Frankie",
  "Gale",
  "Hayden",
  "Iris",
  "Jamie",
  "Kendall",
  "Lennox",
  "Marlowe",
  "Nova",
  "Onyx",
  "Peyton",
  "Reese",
  "Skyler",
  "Tatum",
  "Vale",
  "Wren",
  "Zephyr",
  "Ari",
  "Blair",
  "Cody",
  "Dale",
  "Eden",
  "Fox",
  "Glen",
  "Haven",
];

/**
 * 根据性别生成随机英文名字
 * @param gender 性别：'MALE' | 'FEMALE' | 'OTHER'
 * @returns 随机英文名字
 */
export function generateRandomName(
  gender: "MALE" | "FEMALE" | "OTHER",
): string {
  let nameList: string[];

  switch (gender) {
    case "MALE":
      nameList = MALE_NAMES;
      break;
    case "FEMALE":
      nameList = FEMALE_NAMES;
      break;
    case "OTHER":
      nameList = NEUTRAL_NAMES;
      break;
    default:
      nameList = NEUTRAL_NAMES;
  }

  const firstNameIndex = Math.floor(Math.random() * nameList.length);
  const lastNameIndex = Math.floor(Math.random() * LAST_NAMES.length);

  return `${nameList[firstNameIndex]} ${LAST_NAMES[lastNameIndex]}`;
}

/**
 * 生成随机英文名字（不指定性别）
 * @returns 随机英文名字
 */
export function generateRandomNameAny(): string {
  const allNames = [...MALE_NAMES, ...FEMALE_NAMES, ...NEUTRAL_NAMES];
  const firstNameIndex = Math.floor(Math.random() * allNames.length);
  const lastNameIndex = Math.floor(Math.random() * LAST_NAMES.length);

  return `${allNames[firstNameIndex]} ${LAST_NAMES[lastNameIndex]}`;
}
