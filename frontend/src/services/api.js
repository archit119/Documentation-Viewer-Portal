export async function fetchProjects() {
  return [{ id: '1', title: 'Demo Project', date: '2025-07-23' }];
}

export async function uploadDocs() {
  console.log('Uploading docs...');
}

export async function fetchProjectDocs(id) {
  return `<h1>Generated Documentation for ${id}</h1>`;
}