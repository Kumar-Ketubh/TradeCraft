// mockData.js
// Central mock data for TradeCraft frontend prototype (Week 1)
// Replace with real API calls in a later phase

export const competitors = [
  {
    id: 1,
    name: "Nike",
    website: "https://nike.com",
    status: "active",
    sources: [
      { label: "New Arrivals",  url: "https://www.nike.com/w/new-3n82y" },
      { label: "News & Press",  url: "https://news.nike.com" },
      { label: "Sustainability",url: "https://www.nike.com/sustainability" },
    ],
  },
  {
    id: 2,
    name: "Apple",
    website: "https://apple.com",
    status: "active",
    sources: [
      { label: "Newsroom",      url: "https://www.apple.com/newsroom/" },
      { label: "Product Store", url: "https://www.apple.com/shop/buy-iphone" },
      { label: "Pricing",       url: "https://www.apple.com/shop/product/MQDY3LL/A" },
    ],
  },
  {
    id: 3,
    name: "Samsung",
    website: "https://samsung.com",
    status: "active",
    sources: [
      { label: "Newsroom",      url: "https://news.samsung.com/global" },
      { label: "Mobile Lineup", url: "https://www.samsung.com/global/galaxy/all-galaxy/" },
      { label: "Offers",        url: "https://www.samsung.com/us/smartphones/all-smartphones/" },
    ],
  },
  {
    id: 4,
    name: "Adidas",
    website: "https://adidas.com",
    status: "active",
    sources: [
      { label: "Blog",          url: "https://www.adidas.com/us/blog" },
      { label: "New Drops",     url: "https://www.adidas.com/us/new" },
      { label: "Sale",          url: "https://www.adidas.com/us/sale" },
    ],
  },
  {
    id: 5,
    name: "Sony",
    website: "https://sony.com",
    status: "active",
    sources: [
      { label: "Press Releases",url: "https://www.sony.com/en/articles/press-release-list" },
      { label: "Product News",  url: "https://electronics.sony.com/all-products/c/all-products" },
      { label: "PlayStation",   url: "https://blog.playstation.com" },
    ],
  },
  {
    id: 6,
    name: "Amazon",
    website: "https://amazon.com",
    status: "active",
    sources: [
      { label: "Announcements", url: "https://www.aboutamazon.com/news" },
      { label: "AWS Blog",      url: "https://aws.amazon.com/blogs/aws/" },
      { label: "Devices",       url: "https://www.amazon.com/Amazon-Devices/b?node=2102313011" },
    ],
  },
];

export const stats = {
  competitorsMonitored: 6,
  sourcesConfigured: 18,
  latestScan: "Not Run",
  findings: 0,
};

export const systemStatus = [
  { label: "Frontend", status: "running" },
  { label: "Backend", status: "not_connected" },
  { label: "Database", status: "not_connected" },
  { label: "AI Workflow", status: "not_connected" },
];

export const findings = [];

export const proposalWorkflow = [
  { step: 1, label: "Validated Finding" },
  { step: 2, label: "Evidence" },
  { step: 3, label: "Analysis" },
  { step: 4, label: "Project Proposal" },
];
