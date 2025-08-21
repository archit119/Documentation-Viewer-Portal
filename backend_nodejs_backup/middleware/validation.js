// backend/middleware/validation.js
const Joi = require('joi');

const projectSchema = Joi.object({
  title: Joi.string()
    .min(2)
    .max(200)
    .required()
    .messages({
      'string.empty': 'Project title is required',
      'string.min': 'Title must be at least 2 characters long',
      'string.max': 'Title cannot exceed 200 characters'
    }),
  
  description: Joi.string()
    .max(2000)
    .allow('')
    .messages({
      'string.max': 'Description cannot exceed 2000 characters'
    })
});

const validateProject = (data) => {
  return projectSchema.validate(data);
};

const userSchema = Joi.object({
  name: Joi.string()
    .min(2)
    .max(50)
    .required()
    .messages({
      'string.empty': 'Name is required',
      'string.min': 'Name must be at least 2 characters long'
    }),
  
  email: Joi.string()
    .email()
    .required()
    .messages({
      'string.email': 'Please provide a valid email address',
      'string.empty': 'Email is required'
    }),
  
  password: Joi.string()
    .min(6)
    .required()
    .messages({
      'string.min': 'Password must be at least 6 characters long',
      'string.empty': 'Password is required'
    })
});

const validateUser = (data) => {
  return userSchema.validate(data);
};

const loginSchema = Joi.object({
  email: Joi.string()
    .email()
    .required()
    .messages({
      'string.email': 'Please provide a valid email address',
      'string.empty': 'Email is required'
    }),
  
  password: Joi.string()
    .required()
    .messages({
      'string.empty': 'Password is required'
    })
});

const validateLogin = (data) => {
  return loginSchema.validate(data);
};

module.exports = {
  validateProject,
  validateUser,
  validateLogin
};