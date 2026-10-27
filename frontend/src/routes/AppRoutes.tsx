import React from 'react';
import { Routes, Route } from 'react-router-dom';
import { HomePage } from '../pages/HomePage';
import { RecipeSearchPage } from '../pages/RecipeSearchPage';
import { RecipeDetailPage } from '../pages/RecipeDetailPage';
import { GroceryPage } from '../pages/GroceryPage';
import { CookingPage, CookingPageWithBoundary } from '../pages/CookingPage';
import { PantryPage } from '../pages/PantryPage';
import { ProfilePage } from '../pages/ProfilePage';
import { NotFoundPage } from '../pages/NotFoundPage';
import { LoginPage } from '../pages/LoginPage';
import { RegisterPage } from '../pages/RegisterPage';
import { MealPlanPage } from '../pages/MealPlanPage';
import { ProtectedRoute } from '../components/auth/ProtectedRoute';

export const AppRoutes: React.FC = () => {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/recipes" element={<RecipeSearchPage />} />
      <Route path="/recipes/:id" element={<RecipeDetailPage />} />
      <Route path="/meal-plan" element={<ProtectedRoute><MealPlanPage /></ProtectedRoute>} />
      <Route path="/grocery" element={<ProtectedRoute><GroceryPage /></ProtectedRoute>} />
      <Route path="/cooking" element={<ProtectedRoute><CookingPageWithBoundary /></ProtectedRoute>} />
      <Route path="/cooking/:sessionId" element={<ProtectedRoute><CookingPageWithBoundary /></ProtectedRoute>} />
      <Route path="/pantry" element={<ProtectedRoute><PantryPage /></ProtectedRoute>} />
      <Route path="/profile" element={<ProtectedRoute><ProfilePage /></ProtectedRoute>} />
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
};
