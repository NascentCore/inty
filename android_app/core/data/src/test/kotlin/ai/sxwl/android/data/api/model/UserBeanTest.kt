package ai.sxwl.android.data.api.model

import org.junit.Assert.assertEquals
import org.junit.Test

class UserBeanTest {

    @Test
    fun pronouns_matchGenderOrFallbackToTheyThem() {
        assertEquals("He/Him", UserProfile(gender = GENDER.MALE.value).pronouns())
        assertEquals("She/Her", UserProfile(gender = GENDER.FEMALE.value).pronouns())
        assertEquals("They/Them", UserProfile(gender = "UNKNOWN").pronouns())
        assertEquals("They/Them", UserProfile(gender = null).pronouns())
    }
}
