import axios from 'axios';

async function test() {
  try {
    const loginRes = await axios.post('http://localhost:8000/api/auth/login', new URLSearchParams({
      username: 'admin',
      password: 'admin_password'
    }), {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
    });
    
    const token = loginRes.data.access_token;
    
    const res = await axios.get('http://localhost:8000/api/products?page=1&page_size=1000', {
      headers: { Authorization: `Bearer ${token}` }
    });
    
    console.log("Total returned in API:", res.data.total);
    console.log("Items array length:", res.data.items?.length);
    console.log("Sample item:", res.data.items[0]);
  } catch (err) {
    console.error(err.message);
  }
}
test();
