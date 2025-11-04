import datetime as dt
from datetime import datetime
from decimal import Decimal
from unittest.mock import patch, MagicMock

from core.enums import SalaryType
from django.test import TestCase
from django.utils import timezone
from factories import (
	JobPostFactory, JobFactory, BusinessUserFactory,
	CountryFactory, CurrencyFactory, EmploymentTypeFactory,
	EducationLevelFactory, StateFactory, CityFactory,
	LanguageFactory, SkillFactory, SkillCategoryFactory,
	BusinessModelFactory, DepartmentFactory
)
from jobs.enums import WorkStructureEnum, JobStatusType

from services.job_posting.schema.indeed_xml import JobBase, Source


class JobBaseGetIndeedApplyDataTestCase(TestCase):
    """Test JobBase.get_indeed_apply_data method"""
    
    def test_get_indeed_apply_data_with_valid_data(self):
        """Test get_indeed_apply_data returns properly formatted URL parameters"""
        job_base = JobBase(
            title="Software Engineer",
            date=timezone.now(),
            referencenumber="REF123",
            requisitionid="REQ123",
            url="https://example.com/job/123",
            company="Test Company",
            sourcename="Test Company",
            city="Vancouver",
            state="BC",
            country="Canada",
            postalcode="V6B 1A1",
            streetaddress="123 Main St",
            email="jobs@test.com",
            description="Test description",
            salary="$50000 per year",
            education="Bachelors",
            jobtype="Full-time",
            experience="5 years",
            lastactivitydate=timezone.now(),
            apijobid="job123",
            location="Vancouver, BC, Canada"
        )
        
        result = job_base.get_indeed_apply_data()
        
        # Check that result contains expected keys
        self.assertIn("indeed-apply-apiToken", result)
        self.assertIn("indeed-apply-jobTitle", result)
        self.assertIn("indeed-apply-jobId", result)
        self.assertIn("indeed-apply-jobCompanyName", result)
        self.assertIn("indeed-apply-jobLocation", result)
        self.assertIn("indeed-apply-jobUrl", result)
        self.assertIn("indeed-apply-postUrl", result)
        
        # Check URL encoding
        self.assertIn("Software+Engineer", result)


class JobBaseGetIndeedPeriodTestCase(TestCase):
    """Test JobBase.get_indeed_period method"""
    
    def test_hourly_salary(self):
        """Test hourly salary conversion"""
        result = JobBase.get_indeed_period(SalaryType.HOURLY.value, 25)
        self.assertEqual(result, "25 per hour")
    
    def test_daily_salary(self):
        """Test daily salary conversion"""
        result = JobBase.get_indeed_period(SalaryType.DAILY.value, 200)
        self.assertEqual(result, "200 per day")
    
    def test_weekly_salary(self):
        """Test weekly salary conversion"""
        result = JobBase.get_indeed_period(SalaryType.WEEKLY.value, 1000)
        self.assertEqual(result, "1000 per week")
    
    def test_monthly_salary(self):
        """Test monthly salary conversion"""
        result = JobBase.get_indeed_period(SalaryType.MONTHLY.value, 5000)
        self.assertEqual(result, "5000 per month")
    
    def test_annually_salary(self):
        """Test annual salary conversion"""
        result = JobBase.get_indeed_period(SalaryType.ANNUALLY.value, 60000)
        self.assertEqual(result, "60000 per year")
    
    def test_bi_weekly_salary_single_value(self):
        """Test bi-weekly salary conversion (should divide by 2)"""
        result = JobBase.get_indeed_period(SalaryType.BI_WEEKLY.value, 2000)
        self.assertEqual(result, "1000.0 per week")
    
    def test_bi_monthly_salary_single_value(self):
        """Test bi-monthly salary conversion (should divide by 2)"""
        result = JobBase.get_indeed_period(SalaryType.BI_MONTHLY.value, 10000)
        self.assertEqual(result, "5000.0 per month")
    
    def test_salary_range_hourly(self):
        """Test salary range with hourly rate"""
        result = JobBase.get_indeed_period(SalaryType.HOURLY.value, (20, 30))
        self.assertEqual(result, "20-30 per hour")
    
    def test_salary_range_annually(self):
        """Test salary range with annual salary"""
        result = JobBase.get_indeed_period(SalaryType.ANNUALLY.value, (50000, 70000))
        self.assertEqual(result, "50000-70000 per year")
    
    def test_bi_weekly_salary_range(self):
        """Test bi-weekly salary range (should divide by 2)"""
        result = JobBase.get_indeed_period(SalaryType.BI_WEEKLY.value, (2000, 3000))
        # Result should be a string with divided values
        self.assertIn("per week", result)


class JobBaseGetSalaryTestCase(TestCase):
    """Test JobBase.get_salary method"""
    
    def setUp(self):
        self.currency = CurrencyFactory.create(symbol="$")
        self.job = JobFactory.create()
    
    def test_salary_with_min_only(self):
        """Test salary display with only minimum salary"""
        job_post = JobPostFactory.create(
            job=self.job,
            salary_min=Decimal("50000"),
            salary_max=None,
            salary_type=SalaryType.ANNUALLY.value,
            salary_currency=self.currency
        )
        
        result = JobBase.get_salary(job_post)
        self.assertIn("$", result)
        self.assertIn("50000", result)
        self.assertIn("per year", result)
    
    def test_salary_with_max_only(self):
        """Test salary display with only maximum salary"""
        job_post = JobPostFactory.create(
            job=self.job,
            salary_min=None,
            salary_max=Decimal("70000"),
            salary_type=SalaryType.ANNUALLY.value,
            salary_currency=self.currency
        )
        
        result = JobBase.get_salary(job_post)
        self.assertIn("$", result)
        self.assertIn("70000", result)
        self.assertIn("per year", result)
    
    def test_salary_with_range(self):
        """Test salary display with min and max"""
        job_post = JobPostFactory.create(
            job=self.job,
            salary_min=Decimal("50000"),
            salary_max=Decimal("70000"),
            salary_type=SalaryType.ANNUALLY.value,
            salary_currency=self.currency
        )
        
        result = JobBase.get_salary(job_post)
        self.assertIn("$", result)
        self.assertIn("50000", result)
        self.assertIn("70000", result)
        self.assertIn("per year", result)
    
    def test_salary_with_no_values(self):
        """Test salary display with no salary information"""
        job_post = JobPostFactory.create(
            job=self.job,
            salary_min=None,
            salary_max=None,
            salary_type=SalaryType.ANNUALLY.value,
            salary_currency=self.currency
        )
        
        result = JobBase.get_salary(job_post)
        self.assertEqual(result, "$ 0 per year")
    
    def test_salary_without_currency(self):
        """Test salary display without currency (should default to $)"""
        job_post = JobPostFactory.create(
            job=self.job,
            salary_min=Decimal("50000"),
            salary_max=Decimal("70000"),
            salary_type=SalaryType.ANNUALLY.value,
            salary_currency=None
        )
        
        result = JobBase.get_salary(job_post)
        self.assertIn("$", result)


class JobBaseGetDescriptionTestCase(TestCase):
    """Test JobBase.get_description method"""
    
    @patch('services.job_posting.schema.indeed_xml.render_to_string')
    def test_get_description_calls_render_to_string(self, mock_render):
        """Test that get_description calls render_to_string with correct context"""
        mock_render.return_value = "<html>Test Description</html>"
        
        # Create test data
        job = JobFactory.create(
            title="Software Engineer",
            about="Test job description",
            years_of_experience=5
        )
        job_post = JobPostFactory.create(job=job)
        
        result = JobBase.get_description(job_post)
        
        # Verify render_to_string was called
        mock_render.assert_called_once()
        args, kwargs = mock_render.call_args
        
        # Check that template name is correct
        self.assertEqual(args[0], "jobs/en/indeed_desc.html")
        
        # Check that context contains expected keys
        context = args[1]
        self.assertIn("job_title", context)
        self.assertIn("company_name", context)
        self.assertIn("about_job", context)
    
    def test_get_description_renders_actual_template(self):
        """Test that get_description renders actual HTML correctly"""
        from accounts.models import EducationLevel, Department
        from core.models import Language
        
        # Create comprehensive test data
        education_level = EducationLevelFactory.create(level="Bachelor's Degree")
        language = LanguageFactory.create(name="English")
        department = DepartmentFactory.create(name="Engineering")
        currency = CurrencyFactory.create(symbol="$", name="USD")
        
        job = JobFactory.create(
            title="Senior Software Engineer",
            role=None,
            about="An exciting opportunity to work on cutting-edge technology",
            hiring_company_description="We are a leading tech company",
            years_of_experience=5,
            minimum_education_level=education_level,
            qualification="Bachelor's degree in Computer Science or related field",
            responsibilities=["Write clean code", "Review pull requests", "Mentor junior developers"],
            lunch_break="paid",
            lunch_break_time=30,
            technological_requirement="MacBook",
            first_language=language,
            department=department
        )
        
        job_post = JobPostFactory.create(
            job=job,
            salary_min=Decimal("80000"),
            salary_max=Decimal("120000"),
            salary_type=SalaryType.ANNUALLY.value,
            salary_currency=currency,
            benefits=["Health Insurance", "401k", "Remote Work"]
        )
        
        # Render the description
        result = JobBase.get_description(job_post)
        
        # Verify HTML structure
        self.assertIn("<html", result)
        self.assertIn("</html>", result)
        
        # Verify content is included
        self.assertIn("Senior Software Engineer", result)
        self.assertIn("An exciting opportunity", result)
        self.assertIn("We are a leading tech company", result)
        self.assertIn("5 Years", result)
        self.assertIn("Bachelor's degree", result)  # With |safe filter, apostrophes are not escaped
        self.assertIn("Write clean code", result)
        self.assertIn("Review pull requests", result)
        self.assertIn("Mentor junior developers", result)
        self.assertIn("English", result)
        self.assertIn("Engineering", result)
        
        # Verify no empty sections cause errors
        self.assertNotIn("None", result)
    
    def test_get_description_with_minimal_data(self):
        """Test that get_description works with minimal job data"""
        job = JobFactory.create(
            title="Job Title",
            about=None,
            hiring_company_description=None,
            years_of_experience=None,
            minimum_education_level=None,
            qualification=None,
            responsibilities=[],
            lunch_break=None,
            lunch_break_time=0
        )
        
        job_post = JobPostFactory.create(
            job=job,
            salary_min=None,
            salary_max=None,
            benefits=[]
        )
        
        # Should not raise any errors
        result = JobBase.get_description(job_post)
        
        # Verify basic HTML structure
        self.assertIn("<html", result)
        self.assertIn("</html>", result)
        
        # Verify no "None" strings appear
        self.assertNotIn("None", result)
    
    def test_get_description_with_working_hours(self):
        """Test that get_description renders working hours correctly in HTML"""
        from jobs.models import AvailableDay
        from datetime import time
        
        education_level = EducationLevelFactory.create(level="Bachelor's Degree")
        currency = CurrencyFactory.create(symbol="$", name="USD")
        
        job = JobFactory.create(
            title="Full Stack Developer",
            role=None,
            about="Join our dynamic team",
            hiring_company_description="Leading tech startup",
            years_of_experience=3,
            minimum_education_level=education_level,
            responsibilities=["Develop features", "Code review"],
            lunch_break="paid",
            lunch_break_time=60
        )
        
        # Add multiple working days
        AvailableDay.objects.create(
            job=job,
            day="Monday",
            start_time=time(9, 0),
            end_time=time(17, 30)
        )
        AvailableDay.objects.create(
            job=job,
            day="Tuesday",
            start_time=time(9, 0),
            end_time=time(17, 30)
        )
        AvailableDay.objects.create(
            job=job,
            day="Wednesday",
            start_time=time(10, 0),
            end_time=time(18, 0)
        )
        AvailableDay.objects.create(
            job=job,
            day="Thursday",
            start_time=time(9, 0),
            end_time=time(17, 30)
        )
        AvailableDay.objects.create(
            job=job,
            day="Friday",
            start_time=time(9, 0),
            end_time=time(15, 0)
        )
        
        job_post = JobPostFactory.create(
            job=job,
            salary_min=Decimal("70000"),
            salary_max=Decimal("90000"),
            salary_type=SalaryType.ANNUALLY.value,
            salary_currency=currency,
            benefits=["Health Insurance", "Flexible Hours"]
        )
        
        # Render the description
        result = JobBase.get_description(job_post)
        
        # Verify HTML structure
        self.assertIn("<html", result)
        self.assertIn("<h2>Working Hours</h2>", result)
        
        # Verify all working days are present
        self.assertIn("Monday: 09:00 - 17:30", result)
        self.assertIn("Tuesday: 09:00 - 17:30", result)
        self.assertIn("Wednesday: 10:00 - 18:00", result)
        self.assertIn("Thursday: 09:00 - 17:30", result)
        self.assertIn("Friday: 09:00 - 15:00", result)
        
        # Verify working hours section is properly formatted in list
        self.assertIn("<li>Monday: 09:00 - 17:30</li>", result)
        self.assertIn("<li>Friday: 09:00 - 15:00</li>", result)
        
        # Verify other content is also present
        self.assertIn("Full Stack Developer", result)
        self.assertIn("Join our dynamic team", result)
        self.assertIn("Develop features", result)
        
        # Verify no "None" strings appear
        self.assertNotIn("None", result)


class JobBaseFormatWorkingHoursTestCase(TestCase):
    """Test JobBase._format_working_hours method"""
    
    def test_format_working_hours_with_multiple_days(self):
        """Test formatting multiple available days with times"""
        from jobs.models import AvailableDay
        from datetime import time
        
        job = JobFactory.create()
        
        # Create multiple available days
        AvailableDay.objects.create(
            job=job,
            day="Monday",
            start_time=time(9, 0),
            end_time=time(17, 0)
        )
        AvailableDay.objects.create(
            job=job,
            day="Tuesday",
            start_time=time(9, 0),
            end_time=time(17, 0)
        )
        AvailableDay.objects.create(
            job=job,
            day="Wednesday",
            start_time=time(10, 0),
            end_time=time(18, 0)
        )
        
        result = JobBase._format_working_hours(job)
        
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 3)
        self.assertIn("Monday: 09:00 - 17:00", result)
        self.assertIn("Tuesday: 09:00 - 17:00", result)
        self.assertIn("Wednesday: 10:00 - 18:00", result)
    
    def test_format_working_hours_without_times(self):
        """Test formatting available days without specific times"""
        from jobs.models import AvailableDay
        
        job = JobFactory.create()
        
        AvailableDay.objects.create(
            job=job,
            day="Friday",
            start_time=None,
            end_time=None
        )
        
        result = JobBase._format_working_hours(job)
        
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 1)
        self.assertIn("Friday: Available", result)
    
    def test_format_working_hours_with_no_days(self):
        """Test formatting when there are no available days"""
        job = JobFactory.create()
        
        result = JobBase._format_working_hours(job)
        
        self.assertIsNone(result)
    
    def test_format_working_hours_mixed_formats(self):
        """Test formatting with mix of days with and without times"""
        from jobs.models import AvailableDay
        from datetime import time
        
        job = JobFactory.create()
        
        AvailableDay.objects.create(
            job=job,
            day="Monday",
            start_time=time(9, 0),
            end_time=time(17, 0)
        )
        AvailableDay.objects.create(
            job=job,
            day="Saturday",
            start_time=None,
            end_time=None
        )
        
        result = JobBase._format_working_hours(job)
        
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 2)
        self.assertIn("Monday: 09:00 - 17:00", result)
        self.assertIn("Saturday: Available", result)


class JobBaseGetEducationTestCase(TestCase):
    """Test JobBase.get_education method"""
    
    def test_get_education_with_level(self):
        """Test get_education with education level set"""
        education_level = EducationLevelFactory.create(level="Masters")
        job = JobFactory.create(minimum_education_level=education_level)
        job_post = JobPostFactory.create(job=job)
        
        result = JobBase.get_education(job_post)
        self.assertEqual(result, "Masters")
    
    def test_get_education_without_level(self):
        """Test get_education without education level (should default to Bachelors)"""
        job = JobFactory.create(minimum_education_level=None)
        job_post = JobPostFactory.create(job=job)
        
        result = JobBase.get_education(job_post)
        self.assertEqual(result, "Bachelors")


class JobBaseConvertToJobTestCase(TestCase):
    """Test JobBase.convert_to_job method"""
    
    def setUp(self):
        self.country = CountryFactory.create(name="Canada")
        self.state = StateFactory.create(name="British Columbia")
        self.city = CityFactory.create(name="Vancouver")
        self.currency = CurrencyFactory.create(symbol="$")
        self.employment_type = EmploymentTypeFactory.create(name="Full-time")
        
    def test_convert_to_job_basic(self):
        """Test basic job conversion"""
        job = JobFactory.create(
            title="Software Engineer",
            work_structure=WorkStructureEnum.REMOTE.value,
            employment_type=self.employment_type,
            years_of_experience=5
        )
        job_post = JobPostFactory.create(
            job=job,
            country=self.country,
            province=self.state,
            city=self.city,
            postal_code="V6B 1A1",
            salary_currency=self.currency
        )
        
        result = JobBase.convert_to_job(job_post)
        
        self.assertIsInstance(result, JobBase)
        self.assertEqual(result.title, job.get_title)
        self.assertEqual(result.referencenumber, str(job_post.uid))
        self.assertEqual(result.requisitionid, str(job_post.uid))
        self.assertEqual(result.city, "Vancouver")
        self.assertEqual(result.state, "British Columbia")
        self.assertEqual(result.country, "Canada")
        self.assertEqual(result.postalcode, "V6B 1A1")
        self.assertEqual(result.remotetype, "Fully remote")
    
    def test_convert_to_job_hybrid(self):
        """Test job conversion with hybrid work structure"""
        job = JobFactory.create(
            work_structure=WorkStructureEnum.HYBRID.value,
            employment_type=self.employment_type
        )
        job_post = JobPostFactory.create(
            job=job,
            country=self.country
        )
        
        result = JobBase.convert_to_job(job_post)
        self.assertEqual(result.remotetype, "Hybrid remote")
    
    def test_convert_to_job_with_experience(self):
        """Test job conversion with years of experience"""
        job = JobFactory.create(years_of_experience=5)
        job_post = JobPostFactory.create(job=job, country=self.country)
        
        result = JobBase.convert_to_job(job_post)
        # Note: The method uses years_of_experience (not years_experience as in the code)
        # This might be a bug in the original code
        self.assertIsNotNone(result.experience)


class JobBaseToXmlTestCase(TestCase):
    """Test JobBase.to_xml method"""
    
    def test_to_xml_generates_valid_xml(self):
        """Test that to_xml generates valid XML structure"""
        job_base = JobBase(
            title="Software Engineer",
            date=datetime(2024, 1, 1, 12, 0, 0, tzinfo=dt.timezone.utc),
            referencenumber="REF123",
            requisitionid="REQ123",
            url="https://example.com/job/123",
            company="Test Company",
            sourcename="Test Company",
            city="Vancouver",
            state="BC",
            country="Canada",
            postalcode="V6B 1A1",
            streetaddress="123 Main St",
            email="jobs@test.com",
            description="Test description",
            salary="$50000 per year",
            education="Bachelors",
            jobtype="Full-time",
            experience="5 years",
            lastactivitydate=datetime(2024, 1, 1, 12, 0, 0, tzinfo=dt.timezone.utc),
            apijobid="job123",
            location="Vancouver, BC, Canada"
        )
        
        xml_element = job_base.to_xml()
        
        # Convert to string to check structure
        from xml.etree.ElementTree import tostring
        xml_string = tostring(xml_element, encoding="unicode")
        
        # Check that it contains expected elements
        self.assertIn("<job>", xml_string)
        self.assertIn("</job>", xml_string)
        self.assertIn("CDATA", xml_string)
    
    def test_to_xml_with_optional_fields(self):
        """Test to_xml with optional fields"""
        job_base = JobBase(
            title="Software Engineer",
            date=datetime(2024, 1, 1, 12, 0, 0, tzinfo=dt.timezone.utc),
            referencenumber="REF123",
            requisitionid="REQ123",
            url="https://example.com/job/123",
            company="Test Company",
            sourcename="Test Company",
            city="Vancouver",
            state="BC",
            country="Canada",
            postalcode="V6B 1A1",
            streetaddress="123 Main St",
            email="jobs@test.com",
            description="Test description",
            salary="$50000 per year",
            education="Bachelors",
            jobtype="Full-time",
            experience="5 years",
            lastactivitydate=datetime(2024, 1, 1, 12, 0, 0, tzinfo=dt.timezone.utc),
            category="Technology",
            remotetype="Fully remote",
            billingId="BILL123",
            apijobid="job123",
            location="Vancouver, BC, Canada"
        )
        
        xml_element = job_base.to_xml()
        
        from xml.etree.ElementTree import tostring
        xml_string = tostring(xml_element, encoding="unicode")
        
        # Check optional fields are included
        self.assertIn("category", xml_string)
        self.assertIn("remotetype", xml_string)
        self.assertIn("billingId", xml_string)


class SourceTestCase(TestCase):
    """Test Source class"""
    
    def test_get_data(self):
        """Test Source.get_data returns correct data"""
        source = Source.get_data()
        
        self.assertIsInstance(source, Source)
        self.assertEqual(source.publisher, "1840 GTC")
        self.assertEqual(source.publisherurl, "https://1840gtc.netlify.app")
    
    @patch('services.job_posting.schema.indeed_xml.JobPost.objects')
    def test_to_xml_stream_generates_xml_header(self, mock_jobpost_objects):
        """Test to_xml_stream generates proper XML header"""
        # Mock the iterator to return empty list
        mock_queryset = MagicMock()
        mock_queryset.iterator.return_value = []
        mock_jobpost_objects.select_related.return_value.filter.return_value.order_by.return_value = mock_queryset
        
        result = list(Source.to_xml_stream())
        
        # Check XML header
        self.assertIn('<?xml version="1.0" encoding="UTF-8"?>', result[0])
        self.assertIn('<source>', result[1])
        self.assertIn('</source>', result[-1])
    
    def test_to_xml_stream_includes_job_posts(self):
        """Test to_xml_stream includes job posts"""
        # Create real job post for integration test
        country = CountryFactory.create()
        currency = CurrencyFactory.create(symbol="$")
        employment_type = EmploymentTypeFactory.create()
        
        job = JobFactory.create(
            title="Test Job",
            work_structure=WorkStructureEnum.REMOTE.value,
            employment_type=employment_type
        )
        job_post = JobPostFactory.create(
            job=job,
            country=country,
            status=JobStatusType.POSTED.value,
            salary_currency=currency
        )
        
        # Use real query
        result = list(Source.to_xml_stream())
        
        # Join all parts
        full_xml = "".join(result)
        
        # Check that XML is valid
        self.assertIn('<?xml version="1.0" encoding="UTF-8"?>', full_xml)
        self.assertIn('<source>', full_xml)
        self.assertIn('</source>', full_xml)
        self.assertIn('<job>', full_xml)
    
    @patch('services.job_posting.schema.indeed_xml.Logger')
    @patch('services.job_posting.schema.indeed_xml.JobPost.objects')
    def test_to_xml_stream_handles_errors(self, mock_jobpost_objects, mock_logger):
        """Test to_xml_stream handles errors gracefully"""
        # Create a mock job post that will raise an exception
        mock_job_post = MagicMock()
        mock_job_post.job.get_title = "Test Job"
        
        # Make convert_to_job raise an exception
        with patch.object(JobBase, 'convert_to_job', side_effect=Exception("Test error")):
            mock_queryset = MagicMock()
            mock_queryset.iterator.return_value = [mock_job_post]
            mock_jobpost_objects.select_related.return_value.filter.return_value.order_by.return_value = mock_queryset
            
            result = list(Source.to_xml_stream())
            
            # Check that error was logged
            mock_logger.critical.assert_called()
            
            # Check that XML structure is still valid
            full_xml = "".join(result)
            self.assertIn('<source>', full_xml)
            self.assertIn('</source>', full_xml)


class JobBaseAddElementTestCase(TestCase):
    """Test JobBase.add_element static method"""
    
    def test_add_element_with_text(self):
        """Test add_element adds element with CDATA"""
        from xml.etree.ElementTree import Element, tostring
        
        parent = Element("parent")
        JobBase.add_element(parent, "child", "test text")
        
        xml_string = tostring(parent, encoding="unicode")
        self.assertIn("<child>", xml_string)
        self.assertIn("CDATA", xml_string)
        self.assertIn("test text", xml_string)
    
    def test_add_element_with_empty_text(self):
        """Test add_element does not add element with empty text"""
        from xml.etree.ElementTree import Element, tostring
        
        parent = Element("parent")
        JobBase.add_element(parent, "child", "")
        
        xml_string = tostring(parent, encoding="unicode")
        self.assertNotIn("<child>", xml_string)
    
    def test_add_element_with_none_text(self):
        """Test add_element does not add element with None text"""
        from xml.etree.ElementTree import Element, tostring
        
        parent = Element("parent")
        JobBase.add_element(parent, "child", None)
        
        xml_string = tostring(parent, encoding="unicode")
        self.assertNotIn("<child>", xml_string)


class IntegrationTestCase(TestCase):
    """Integration tests for the full workflow"""
    
    def test_full_job_post_to_xml_workflow(self):
        """Test complete workflow from JobPost to XML"""
        # Create all necessary objects
        country = CountryFactory.create(name="Canada")
        state = StateFactory.create(name="British Columbia")
        city = CityFactory.create(name="Vancouver")
        currency = CurrencyFactory.create(symbol="$", name="CAD")
        employment_type = EmploymentTypeFactory.create(name="Full-time")
        education_level = EducationLevelFactory.create(level="Bachelors")
        
        # Create job with all details
        job = JobFactory.create(
            title="Senior Software Engineer",
            work_structure=WorkStructureEnum.REMOTE.value,
            employment_type=employment_type,
            years_of_experience=5,
            minimum_education_level=education_level,
            about="Great job opportunity"
        )
        
        # Create job post
        job_post = JobPostFactory.create(
            job=job,
            country=country,
            province=state,
            city=city,
            postal_code="V6B 1A1",
            salary_min=Decimal("80000"),
            salary_max=Decimal("120000"),
            salary_type=SalaryType.ANNUALLY.value,
            salary_currency=currency,
            status=JobStatusType.POSTED.value
        )
        
        # Convert to JobBase
        job_base = JobBase.convert_to_job(job_post)
        
        # Verify JobBase attributes
        self.assertIsNotNone(job_base)
        self.assertEqual(job_base.city, "Vancouver")
        self.assertEqual(job_base.state, "British Columbia")
        self.assertEqual(job_base.country, "Canada")
        self.assertIn("80000", job_base.salary)
        self.assertIn("120000", job_base.salary)
        
        # Convert to XML
        xml_element = job_base.to_xml()
        
        # Verify XML is valid
        self.assertIsNotNone(xml_element)
        self.assertEqual(xml_element.tag, "job")
        
        # Check XML contains data
        from xml.etree.ElementTree import tostring
        xml_string = tostring(xml_element, encoding="unicode")
        self.assertIn("Vancouver", xml_string)
        self.assertIn("British Columbia", xml_string)
