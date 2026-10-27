"""
DishIQ Phase 5 — Unit Intelligence & Conversion Tests
Tests for centralized unit normalization, dimensionality, compatibility, and conversion.
"""
import math
import pytest
from app.ingredient_intelligence.units import (
    UnitDimension,
    normalize_unit,
    get_unit_dimension,
    are_units_compatible,
    convert_quantity,
    format_quantity_and_unit,
)


class TestUnitNormalization:
    def test_mass_units(self):
        assert normalize_unit("g") == "g"
        assert normalize_unit("grams") == "g"
        assert normalize_unit("gram") == "g"
        assert normalize_unit("kg") == "kg"
        assert normalize_unit("kilograms") == "kg"
        assert normalize_unit("oz") == "oz"
        assert normalize_unit("ounces") == "oz"
        assert normalize_unit("lb") == "lb"
        assert normalize_unit("pounds") == "lb"
        assert normalize_unit("mg") == "mg"

    def test_volume_units(self):
        assert normalize_unit("ml") == "ml"
        assert normalize_unit("milliliters") == "ml"
        assert normalize_unit("l") == "l"
        assert normalize_unit("litres") == "l"
        assert normalize_unit("tsp") == "tsp"
        assert normalize_unit("teaspoon") == "tsp"
        assert normalize_unit("tbsp") == "tbsp"
        assert normalize_unit("tablespoon") == "tbsp"
        assert normalize_unit("cup") == "cup"
        assert normalize_unit("cups") == "cup"
        assert normalize_unit("fl oz") == "fl oz"

    def test_count_and_descriptive(self):
        assert normalize_unit("piece") == "piece"
        assert normalize_unit("pieces") == "piece"
        assert normalize_unit("clove") == "clove"
        assert normalize_unit("cloves") == "clove"
        assert normalize_unit("pinch") == "pinch"
        assert normalize_unit("bunch") == "bunch"
        assert normalize_unit("to taste") == "to taste"

    def test_none_and_empty(self):
        assert normalize_unit(None) is None
        assert normalize_unit("") is None
        assert normalize_unit("   ") is None


class TestUnitDimensionality:
    def test_dimensions(self):
        assert get_unit_dimension("grams") == UnitDimension.MASS
        assert get_unit_dimension("kg") == UnitDimension.MASS
        assert get_unit_dimension("lb") == UnitDimension.MASS
        assert get_unit_dimension("ml") == UnitDimension.VOLUME
        assert get_unit_dimension("cup") == UnitDimension.VOLUME
        assert get_unit_dimension("tbsp") == UnitDimension.VOLUME
        assert get_unit_dimension("piece") == UnitDimension.COUNT
        assert get_unit_dimension("pinch") == UnitDimension.DESCRIPTIVE
        assert get_unit_dimension("unknown_unit_xyz") is None


class TestUnitCompatibility:
    def test_compatible_mass_units(self):
        assert are_units_compatible("g", "kg") is True
        assert are_units_compatible("kg", "g") is True
        assert are_units_compatible("lb", "oz") is True
        assert are_units_compatible("g", "lb") is True

    def test_compatible_volume_units(self):
        assert are_units_compatible("ml", "l") is True
        assert are_units_compatible("tbsp", "tsp") is True
        assert are_units_compatible("cup", "ml") is True
        assert are_units_compatible("fl oz", "tbsp") is True

    def test_incompatible_mass_and_volume(self):
        # Universal rule: cannot convert mass to volume without density
        assert are_units_compatible("g", "ml") is False
        assert are_units_compatible("kg", "l") is False
        assert are_units_compatible("cup", "g") is False
        assert are_units_compatible("tbsp", "gram") is False

    def test_incompatible_with_count_or_descriptive(self):
        assert are_units_compatible("piece", "kg") is False
        assert are_units_compatible("pinch", "cup") is False
        assert are_units_compatible("bunch", "gram") is False


class TestQuantityConversion:
    def test_mass_conversions(self):
        # 1000g -> 1.0kg
        val, unit = convert_quantity(1000.0, "g", "kg")
        assert math.isclose(val, 1.0, abs_tol=1e-4)
        assert unit == "kg"

        # 2.5kg -> 2500g
        val, unit = convert_quantity(2.5, "kg", "g")
        assert math.isclose(val, 2500.0, abs_tol=1e-4)
        assert unit == "g"

        # 1 lb -> ~453.59g
        val, unit = convert_quantity(1.0, "lb", "g")
        assert math.isclose(val, 453.5924, abs_tol=1e-2)
        assert unit == "g"

        # 16 oz -> 1.0 lb
        val, unit = convert_quantity(16.0, "oz", "lb")
        assert math.isclose(val, 1.0, abs_tol=1e-2)
        assert unit == "lb"

    def test_volume_conversions(self):
        # 1 tbsp -> 3 tsp
        val, unit = convert_quantity(1.0, "tbsp", "tsp")
        assert math.isclose(val, 3.0, abs_tol=1e-2)
        assert unit == "tsp"

        # 1 cup -> 16 tbsp
        val, unit = convert_quantity(1.0, "cup", "tbsp")
        assert math.isclose(val, 16.0, abs_tol=1e-2)
        assert unit == "tbsp"

        # 1 litre -> 1000 ml
        val, unit = convert_quantity(1.0, "l", "ml")
        assert math.isclose(val, 1000.0, abs_tol=1e-4)
        assert unit == "ml"

    def test_rejection_of_incompatible_conversion(self):
        # Mass to volume rejection
        val, err = convert_quantity(500.0, "g", "ml")
        assert val is None
        assert "Incompatible conversion" in err

        # Volume to mass rejection
        val, err = convert_quantity(2.0, "cup", "g")
        assert val is None
        assert "Incompatible conversion" in err

        # Unknown unit rejection
        val, err = convert_quantity(10.0, "unknown_xyz", "g")
        assert val is None
        assert "unknown" in err.lower()


class TestQuantityFormatting:
    def test_formats(self):
        assert format_quantity_and_unit(1.0, "kg") == "1 kg"
        assert format_quantity_and_unit(1.5, "kg") == "1.5 kg"
        assert format_quantity_and_unit(2.0, "cup") == "2 cups"
        assert format_quantity_and_unit(1.0, "cup") == "1 cup"
        assert format_quantity_and_unit(None, "pinch") == "pinch"


class TestHeuristicCrossDimensionConversions:
    def test_compatibility_with_ingredient_heuristics(self):
        # Without ingredient name: incompatible
        assert are_units_compatible("pieces", "g") is False
        assert are_units_compatible("tsp", "g") is False

        # With ingredient name: compatible via heuristics
        assert are_units_compatible("pieces", "g", ingredient_name="tomato") is True
        assert are_units_compatible("pieces", "kg", ingredient_name="tomato") is True
        assert are_units_compatible("tsp", "g", ingredient_name="cumin seeds") is True
        assert are_units_compatible("bunch", "g", ingredient_name="coriander") is True
        assert are_units_compatible("clove", "g", ingredient_name="garlic") is True

    def test_quantity_conversion_with_heuristics(self):
        # 2 pieces of tomato -> 200g
        val, unit = convert_quantity(2.0, "pieces", "g", ingredient_name="tomato")
        assert val == 200.0
        assert unit == "g"

        # 200g tomato -> 2 pieces
        val, unit = convert_quantity(200.0, "g", "piece", ingredient_name="tomato")
        assert val == 2.0
        assert unit == "piece"

        # 1 tsp cumin seeds (4.93ml * 0.65 density = ~3.2g)
        val, unit = convert_quantity(1.0, "tsp", "g", ingredient_name="cumin seeds")
        assert math.isclose(val, 3.2038, abs_tol=1e-2)
        assert unit == "g"

        # 1 bunch coriander -> 100g
        val, unit = convert_quantity(1.0, "bunch", "g", ingredient_name="coriander")
        assert val == 100.0
        assert unit == "g"

        # 4 cloves garlic -> 16g
        val, unit = convert_quantity(4.0, "clove", "g", ingredient_name="garlic")
        assert val == 16.0
        assert unit == "g"
