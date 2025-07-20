// server.js
require('dotenv').config();
const express = require('express');
const mongoose = require('mongoose');
const cors = require('cors');

const app = express();
app.use(cors());
app.use(express.json());

// Connect to MongoDB Atlas
mongoose.connect(process.env.MONGODB_URI, {
  useNewUrlParser: true,
  useUnifiedTopology: true,
})
.then(() => console.log("✅ CLARA MongoDB connected"))
.catch(err => console.error("❌ CLARA MongoDB error:", err));

// Routes
const userRoutes = require('./routes/userRoutes');
app.use('/api/users', userRoutes);

// Server start
const PORT = process.env.PORT || 8000;
app.listen(PORT, () => console.log(`🚀 CLARA backend running on http://localhost:${PORT}`));
