package ai.sxwl.android.data.api.model

import org.junit.Assert.assertEquals
import org.junit.Test

class UserProfilePronounsTest {

    @Test
    fun pronouns_returnsHeHimForMale() {
        val profile = UserProfile(gender = GENDER.MALE.value)

        assertEquals("He/Him", profile.pronouns())
    }

    @Test
    fun pronouns_returnsSheHerForFemale() {
        val profile = UserProfile(gender = GENDER.FEMALE.value)

        assertEquals("She/Her", profile.pronouns())
    }

    @Test
    fun pronouns_defaultsToTheyThemWhenGenderMissingOrUnknown() {
        val nullGenderProfile = UserProfile(gender = null)
        val unknownGenderProfile = UserProfile(gender = "NON_BINARY")

        assertEquals("They/Them", nullGenderProfile.pronouns())
        assertEquals("They/Them", unknownGenderProfile.pronouns())
    }
}
